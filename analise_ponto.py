import re
import numpy as np
import pandas as pd

INTERVALO_PADRAO_MIN = 30
TOLERANCIA_INTERVALO_MIN = 3
MADRUGADA_LIMITE_MIN = 6 * 60
GAP_ENTRADA_SUSPEITO_MIN = 4 * 60
DIAS_VALIDOS = {'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom', 'Sab'}

# Colunas atualizadas (removido CPF, Funcao, Setor e adicionado as da Escala)
COLUNAS_EXPORT = [
    'Motorista', 'Matricula', 'Periodo', 'Data', 'DIA', 
    'INIC', 'I.INT', 'F.INT', 'FIM', 'Intervalo',
    'Escala Prevista', 'Escala Início', 'Escala Fim',
    'PREVISTA', 'EXTRA', 'DEB', 'TOTAL', 'A.NOT', 'OCOR',
    'Tipo', 'Motivo', 'Criticidade'
]

def time_str_to_mins(s):
    if s is None or (isinstance(s, float) and np.isnan(s)): return None
    s = str(s).strip()
    if s in ('---', '', 'FOLGA', 'NaN', '00:00'): return None
    try:
        parts = s.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

def mins_to_str(m):
    if m is None: return ''
    h = int(m // 60) % 24
    mins = int(m % 60)
    return f'{h:02d}:{mins:02d}'

def format_duracao_min(minutos):
    if minutos is None: return '---'
    h = int(minutos // 60)
    m = int(minutos % 60)
    return f'{h:02d}:{m:02d}'

def normalizar_cronologico(base, valor):
    if valor is None: return None
    return valor if valor >= base else valor + 1440

def duracao_intervalo_min(i_int, f_int):
    if i_int is None or f_int is None: return None
    c_fint = f_int if f_int >= i_int else f_int + 1440
    return c_fint - i_int

def intervalo_valido(i_int, f_int):
    duracao = duracao_intervalo_min(i_int, f_int)
    if duracao is None: return None
    return abs(duracao - INTERVALO_PADRAO_MIN) <= TOLERANCIA_INTERVALO_MIN

def desvio_circular(valor, referencia):
    return min(abs(valor - referencia), abs(valor + 1440 - referencia), abs(valor - 1440 - referencia))

def extrair_cpf_admissao(line):
    cpf = re.search(r'Cpf:\s*([\d.\-]+)', line, re.I)
    adm = re.search(r'Dt\.\s*Admiss[a-zA-ZãéÃÉ]*o:\s*(\d{2}/\d{2}/\d{4})', line, re.I)
    return {'CPF': cpf.group(1).strip() if cpf else '', 'Admissao': adm.group(1).strip() if adm else ''}

def parsear_escala(caminho_escala):
    """Lê o arquivo de escala e mapeia {('Matricula', 'DD/MM'): {'Inicio', 'Fim', 'Escala'}}"""
    escala_dict = {}
    if not caminho_escala:
        return escala_dict
        
    data_atual = ""
    try:
        with open(caminho_escala, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith("Data :"):
                    # Extrai "10/06" de "Data : 10/06/2026"
                    data_completa = line.split(":")[1].strip()
                    data_atual = data_completa[:5] 
                    continue
                
                parts = line.split(';')
                if len(parts) > 10 and data_atual:
                    cracha = parts[6].replace('"', '').strip()
                    if cracha: # Se tem crachá
                        inicio = parts[0].replace('"', '').strip()
                        # Procura o último FIM preenchido nas posições 1, 3 e 5
                        fim = parts[5].replace('"', '').strip() or parts[3].replace('"', '').strip() or parts[1].replace('"', '').strip()
                        nome_escala = parts[8].replace('"', '').strip()
                        
                        escala_dict[(cracha, data_atual)] = {
                            'Inicio': inicio, 'Fim': fim, 'Escala': nome_escala
                        }
    except Exception as e:
        print(f"Erro ao ler escala: {e}")
    return escala_dict

def parsear_planilha(caminho_arquivo):
    linhas = []
    motorista_atual = 'Desconhecido'
    meta_atual = {}
    
    with open(caminho_arquivo, 'r', encoding='latin1', errors='ignore') as f:
        for line in f:
            line_upper = line.upper().strip()
            ctps_idx = line_upper.find('CTPS')

            if ctps_idx != -1 and ':' in line:
                motorista_atual = line[:ctps_idx].split(':')[-1].strip()
                mat = re.match(r'^(\d+)\s*-\s*(.+)$', motorista_atual)
                meta_atual = {
                    'Motorista': motorista_atual,
                    'Matricula': mat.group(1) if mat else '',
                    'Periodo': ''
                }
                continue

            if ('PERÍODO' in line_upper or 'PERIODO' in line_upper) and meta_atual.get('Motorista'):
                p = re.search(r'Per[ií]odo:\s*([^;]+?)\s{2,}Setor', line, re.I)
                meta_atual['Periodo'] = p.group(1).strip() if p else ''
                continue

            parts = line.strip().split(';')
            if len(parts) < 12: continue

            dia = parts[1].strip()
            data = parts[0].replace('*', '').strip()
            
            if dia in DIAS_VALIDOS and data:
                registro = {
                    **meta_atual, 'DATA': data, 'DIA': dia,
                    'INIC': parts[2].strip(), 'I.INT': parts[3].strip(),
                    'F.INT': parts[4].strip(), 'FIM': parts[5].strip(),
                    'PREVISTA': parts[6].strip(), 'EXTRA': parts[7].strip(),
                    'DEB': parts[8].strip(), 'TOTAL': parts[9].strip(),
                    'A.NOT': parts[10].strip(), 'OCOR': parts[11].strip()
                }
                linhas.append(registro)

    return linhas

def montar_erro(motorista, data, tipo, motivo, criticidade, row, info_escala=None):
    i_int = time_str_to_mins(row.get('I.INT'))
    f_int = time_str_to_mins(row.get('F.INT'))
    
    if info_escala is None:
        info_escala = {'Escala': '---', 'Inicio': '---', 'Fim': '---'}

    return {
        'Motorista': motorista,
        'Matricula': row.get('Matricula', ''),
        'Periodo': row.get('Periodo', ''),
        'Data': data, 'DIA': row.get('DIA', ''),
        'INIC': row.get('INIC', '---'), 'I.INT': row.get('I.INT', '---'),
        'F.INT': row.get('F.INT', '---'), 'FIM': row.get('FIM', '---'),
        'Intervalo': format_duracao_min(duracao_intervalo_min(i_int, f_int)),
        'Escala Prevista': info_escala['Escala'],
        'Escala Início': info_escala['Inicio'],
        'Escala Fim': info_escala['Fim'],
        'PREVISTA': row.get('PREVISTA', '---'), 'EXTRA': row.get('EXTRA', '---'),
        'DEB': row.get('DEB', '---'), 'TOTAL': row.get('TOTAL', '---'),
        'A.NOT': row.get('A.NOT', '---'), 'OCOR': row.get('OCOR', ''),
        'Tipo': tipo, 'Motivo': motivo, 'Criticidade': criticidade,
    }

def analisar_planilha(caminho_ponto, caminho_escala=None):
    linhas_ponto = parsear_planilha(caminho_ponto)
    escala_dict = parsear_escala(caminho_escala)
    
    if not linhas_ponto:
        return pd.DataFrame(), 0

    df_linhas = pd.DataFrame(linhas_ponto)
    inconsistencias = []

    for motorista, df_mot in df_linhas.groupby('Motorista'):
        start_times = [time_str_to_mins(v) for v in df_mot['INIC']]
        start_times = [t for t in start_times if t is not None]
        mediana_entrada = float(np.median(start_times)) if start_times else 0

        for _, row in df_mot.iterrows():
            data = row['DATA']
            matricula = row.get('Matricula', '')
            
            # Puxa a escala desse dia
            info_escala = escala_dict.get((matricula, data), None)

            inic_s = str(row['INIC']).strip()
            fim_s = str(row['FIM']).strip()
            
            # --- NOVA REGRA: Tem escala, mas o ponto está vazio, 00:00 ou FOLGA ---
            if info_escala:
                if inic_s in ('---', '', 'FOLGA', '00:00', 'NaN') and fim_s in ('---', '', 'FOLGA', '00:00', 'NaN'):
                    inconsistencias.append(montar_erro(
                        motorista, data, 'Sem Ponto (Escalado)',
                        f"Motorista possivelmente trabalhou nesse dia. Estava escalado ({info_escala['Inicio']} às {info_escala['Fim']}) mas não bateu o ponto.",
                        'Alta', row, info_escala
                    ))
                    continue # Pula as outras regras já que o dia está vazio

            if inic_s in ('---', '', 'FOLGA', '00:00', 'NaN') and fim_s in ('---', '', 'FOLGA', '00:00', 'NaN'):
                continue # Ignora dias de folga reais (sem escala)

            inic = time_str_to_mins(row['INIC'])
            i_int = time_str_to_mins(row['I.INT'])
            f_int = time_str_to_mins(row['F.INT'])
            fim = time_str_to_mins(row['FIM'])

            punches = [inic, i_int, f_int, fim]
            punch_names = ['INIC', 'I.INT', 'F.INT', 'FIM']
            preenchidos = [p for p in punches if p is not None]

            if 0 < len(preenchidos) < 4:
                if i_int is None and f_int is None:
                    inconsistencias.append(montar_erro(motorista, data, 'Sem Intervalo', 'Intervalo não registado', 'Média', row, info_escala))
                else:
                    ausentes = [punch_names[i] for i, p in enumerate(punches) if p is None]
                    inconsistencias.append(montar_erro(motorista, data, 'Batida Faltante', f"Ausência de: {', '.join(ausentes)}", 'Alta', row, info_escala))

            if all(p is not None for p in punches):
                c_iint = normalizar_cronologico(inic, i_int)
                c_fint = normalizar_cronologico(c_iint, f_int)
                c_fim = normalizar_cronologico(c_fint, fim)

                if not (inic <= c_iint <= c_fint <= c_fim):
                    inconsistencias.append(montar_erro(motorista, data, 'Sequência Inválida', 'Horários fora de ordem cronológica', 'Alta', row, info_escala))

                if 0 <= (c_fim - c_fint) <= 2:
                    inconsistencias.append(montar_erro(motorista, data, 'Saída Falsa (Sistema)', 'Saída batida logo após voltar do intervalo. Provável esquecimento de batida real.', 'Alta', row, info_escala))

            if inic is not None and fim is not None:
                c_fim_temp = fim if fim >= inic else fim + 1440
                duracao_total = c_fim_temp - inic
                
                is_virada = False
                if i_int is not None and f_int is not None:
                    c_iint_temp = normalizar_cronologico(inic, i_int)
                    c_fint_temp = normalizar_cronologico(c_iint_temp, f_int)
                    if (c_fim_temp - c_fint_temp) > 540:
                        is_virada = True
                        inconsistencias.append(montar_erro(motorista, data, 'Jornada Agrupada (Erro Virada)', 'Motorista direto da volta do intervalo até a saída. O sistema mesclou dias.', 'Alta', row, info_escala))

                if not is_virada and duracao_total > 840:
                    inconsistencias.append(montar_erro(motorista, data, 'Jornada Extensa (Real)', 'Jornada muito longa. Verificar HE.', 'Média', row, info_escala))

    df_erros = pd.DataFrame(inconsistencias)
    if not df_erros.empty:
        ordem = {'Alta': 1, 'Média': 2, 'Baixa': 3}
        df_erros['_ordem'] = df_erros['Criticidade'].map(ordem)
        df_erros = df_erros.sort_values(['_ordem', 'Motorista', 'Data']).drop('_ordem', axis=1)
        df_erros = df_erros[COLUNAS_EXPORT]

    return df_erros, df_linhas['Motorista'].nunique()

def exportar_relatorios(df_erros, pasta_saida):
    import os
    os.makedirs(pasta_saida, exist_ok=True)
    caminho_xlsx = os.path.join(pasta_saida, 'Relatorio_Falhas_Ponto.xlsx')
    caminho_csv = os.path.join(pasta_saida, 'Relatorio_Falhas_Ponto.csv')
    
    if df_erros.empty:
        pd.DataFrame(columns=COLUNAS_EXPORT).to_excel(caminho_xlsx, index=False, engine='openpyxl')
        pd.DataFrame(columns=COLUNAS_EXPORT).to_csv(caminho_csv, sep=';', index=False, encoding='utf-8-sig')
    else:
        df_erros.to_excel(caminho_xlsx, index=False, engine='openpyxl')
        df_erros.to_csv(caminho_csv, sep=';', index=False, encoding='utf-8-sig')
    return caminho_xlsx, caminho_csv
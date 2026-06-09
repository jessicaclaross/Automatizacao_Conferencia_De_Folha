import pandas as pd
import numpy as np

def time_str_to_mins(s):
    if pd.isna(s): return None
    s = str(s).strip()
    if s in ['---', '', 'FOLGA', 'NaN', '00:00']: return None
    try:
        parts = s.split(':')
        return int(parts[0]) * 60 + int(parts[1])
    except:
        return None

def mins_to_str(m):
    if m is None: return ""
    h = int(m // 60) % 24
    mins = int(m % 60)
    return f"{h:02d}:{mins:02d}"

def processar_arquivo_mestre(caminho_arquivo):
    print(f"⏳ A ler o ficheiro e a separar os motoristas...")
    
    linhas_dados = []
    motorista_atual = "Desconhecido"
    
    try:
        # Alterado para 'latin1', que é o padrão de sistemas que exportam CSV no Windows
        with open(caminho_arquivo, 'r', encoding='latin1', errors='ignore') as f:
            for line in f:
                line_upper = line.upper().strip()
                
                # Nova âncora: Procurar por "CTPS" (não tem acentos, não sofre com erros de codificação)
                if "CTPS" in line_upper and ":" in line:
                    # Corta a linha na palavra "CTPS" e pega a parte esquerda
                    parte_esquerda = line.split("CTPS", 1)[0] # "Funcionário: 30060664 - CLAUDINEI DE PAULA LANA    "
                    # Corta nos dois pontos ':' e pega o nome limpo
                    motorista_atual = parte_esquerda.split(":", 1)[-1].strip()
                else:
                    parts = line.strip().split(';')
                    if len(parts) >= 12:
                        dia = parts[1].strip()
                        if dia in ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom', 'Sab']:
                            data = parts[0].replace('*', '').strip()
                            linhas_dados.append([
                                motorista_atual, data, dia, 
                                parts[2].strip(), parts[3].strip(), 
                                parts[4].strip(), parts[5].strip()
                            ])
    except FileNotFoundError:
        print(f"❌ ERRO: O ficheiro não foi encontrado no caminho especificado!")
        return

    df_completo = pd.DataFrame(linhas_dados, columns=['Motorista', 'DATA', 'DIA', 'INIC', 'I.INT', 'F.INT', 'FIM'])
    
    if df_completo.empty:
        print("❌ Nenhum dado de ponto válido foi encontrado. Verifique o ficheiro CSV.")
        return

    inconsistencias = []

    for motorista, df_mot in df_completo.groupby('Motorista'):
        start_times = []
        for _, row in df_mot.iterrows():
            m = time_str_to_mins(row['INIC'])
            if m is not None: start_times.append(m)
        mediana_entrada = np.median(start_times) if start_times else 0

        for idx, row in df_mot.iterrows():
            data = row['DATA']
            inic = time_str_to_mins(row['INIC'])
            i_int = time_str_to_mins(row['I.INT'])
            f_int = time_str_to_mins(row['F.INT'])
            fim = time_str_to_mins(row['FIM'])
            
            punches = [inic, i_int, f_int, fim]
            punch_names = ['INIC', 'I.INT', 'F.INT', 'FIM']
            
            preenchidos = [p for p in punches if p is not None]
            if 0 < len(preenchidos) < 4:
                if i_int is None and f_int is None:
                    inconsistencias.append({
                        'Motorista': motorista, 'Data': data, 'Tipo': 'Sem Intervalo',
                        'Horário': f"INIC: {row['INIC']}, FIM: {row['FIM']}",
                        'Motivo': 'Intervalo não registado (---)', 'Criticidade': 'Média'
                    })
                else:
                    ausentes = [punch_names[i] for i, p in enumerate(punches) if p is None]
                    inconsistencias.append({
                        'Motorista': motorista, 'Data': data, 'Tipo': 'Batida Faltante',
                        'Horário': f"{row['INIC']} | {row['I.INT']} | {row['F.INT']} | {row['FIM']}",
                        'Motivo': f"Ausência de: {', '.join(ausentes)}", 'Criticidade': 'Alta'
                    })

            if inic is not None and i_int is not None and f_int is not None and fim is not None:
                c_iint = i_int if i_int >= inic else i_int + 1440
                c_fint = f_int if f_int >= c_iint else f_int + 1440
                c_fim = fim if fim >= c_fint else fim + 1440
                
                if not (inic <= c_iint <= c_fint <= c_fim):
                    inconsistencias.append({
                        'Motorista': motorista, 'Data': data, 'Tipo': 'Sequência Inválida',
                        'Horário': f"{row['INIC']} -> {row['I.INT']} -> {row['F.INT']} -> {row['FIM']}",
                        'Motivo': 'Horários em ordem cronológica incorreta', 'Criticidade': 'Alta'
                    })
                    
                duracao_int = c_fint - c_iint
                if duracao_int > 120:
                    inconsistencias.append({
                        'Motorista': motorista, 'Data': data, 'Tipo': 'Intervalo muito longo',
                        'Horário': f"I.INT: {row['I.INT']} / F.INT: {row['F.INT']}",
                        'Motivo': f"Intervalo de {duracao_int} minutos (Acima de 2h)", 'Criticidade': 'Média'
                    })

            if inic is not None:
                desvio = min(abs(inic - mediana_entrada), abs(inic + 1440 - mediana_entrada), abs(inic - 1440 - mediana_entrada))
                if desvio > 240:
                    inconsistencias.append({
                        'Motorista': motorista, 'Data': data, 'Tipo': 'Fora do padrão',
                        'Horário': f"Entrada: {row['INIC']}",
                        'Motivo': f"Horário incomum. Habitual próximo de {mins_to_str(mediana_entrada)}", 'Criticidade': 'Baixa'
                    })

    df_erros = pd.DataFrame(inconsistencias)
    if not df_erros.empty:
        ordem_crit = {'Alta': 1, 'Média': 2, 'Baixa': 3}
        df_erros['Ordem'] = df_erros['Criticidade'].map(ordem_crit)
        df_erros = df_erros.sort_values(['Ordem', 'Motorista']).drop('Ordem', axis=1)
        
        nome_saida = "Relatorio_Falhas_Ponto.csv"
        df_erros.to_csv(nome_saida, sep=';', index=False, encoding='utf-8-sig')
        print(f"\n✅ Análise concluída com sucesso!")
        print(f"🚨 Foram encontrados {len(df_erros)} registos suspeitos.")
        print(f"📊 O ficheiro '{nome_saida}' foi gerado na mesma pasta do seu script.")
    else:
        print("\n✅ Análise concluída! Nenhum erro encontrado na folha!")

# ====================================================================
# EXECUÇÃO DO CÓDIGO
# ====================================================================
caminho_do_seu_arquivo = r"C:\Users\RH\OneDrive\Desktop\Automatizacao_Conferencia_Folha\Automatizacao_Conferencia_De_Folha\_tmp_csv_tmpQNyuut.csv"
processar_arquivo_mestre(caminho_do_seu_arquivo)
import os
import sys
from analise_ponto import analisar_planilha, exportar_relatorios

# ========== COLOQUE OS CAMINHOS AQUI ==========
CAMINHO_PLANILHA = r"C:\Users\lukin\Downloads\planilha analise.csv"
CAMINHO_ESCALA = r"C:\Users\lukin\Downloads\escala_exportada.csv"  # Deixe vazio "" se não tiver escala
# ===============================================

def processar_arquivo_mestre(caminho_ponto, caminho_escala):
    print('A ler os ficheiros de Ponto e Escala...')

    # Se a string da escala estiver vazia ou o arquivo não existir, passa None
    if not caminho_escala or not os.path.isfile(caminho_escala):
        print("[Aviso] Arquivo de Escala não fornecido ou não encontrado. Analisando apenas Ponto.")
        caminho_escala = None

    df_erros, total_motoristas = analisar_planilha(caminho_ponto, caminho_escala)
    pasta_saida = os.path.dirname(os.path.abspath(caminho_ponto))
    caminho_xlsx, caminho_csv = exportar_relatorios(df_erros, pasta_saida)

    if df_erros.empty:
        print('\nNenhum erro encontrado na folha!')
    else:
        print(f'\nAnalise concluida! {total_motoristas} motoristas, {len(df_erros)} registos suspeitos.')

    print(f'\nExcel: {caminho_xlsx}')
    print(f'CSV:   {caminho_csv}')

def aguardar_saida():
    if sys.stdin.isatty(): input('\nPressione Enter para sair...')

def main():
    if not os.path.isfile(CAMINHO_PLANILHA):
        print('Arquivo de Ponto nao encontrado!')
        print(f'Caminho configurado: {CAMINHO_PLANILHA}')
        aguardar_saida()
        return 1

    try:
        processar_arquivo_mestre(CAMINHO_PLANILHA, CAMINHO_ESCALA)
    except Exception as e:
        print(f'\nErro: {e}')
        aguardar_saida()
        return 1

    aguardar_saida()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
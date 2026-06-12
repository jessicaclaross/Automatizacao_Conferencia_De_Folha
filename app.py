import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from analise_ponto import analisar_planilha, exportar_relatorios

class AppAnalisePonto(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Automatização Processo Folha')
        self.geometry('600x520')
        self.minsize(500, 450)
        self.configure(bg='#f0f0f0')

        self.arquivo_ponto = None
        self.arquivo_escala = None
        self.pasta_saida = None
        self.caminho_xlsx = None
        self.df_erros = None
        self.total_motoristas = 0

        self._montar_ui()

    def _montar_ui(self):
        estilo = ttk.Style()
        estilo.theme_use('clam')
        estilo.configure('TFrame', background='#f0f0f0')
        estilo.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 10))
        estilo.configure('Title.TLabel', font=('Segoe UI', 18, 'bold'), foreground='#c0392b')
        estilo.configure('Sub.TLabel', foreground='#555555', font=('Segoe UI', 9))
        estilo.configure('TButton', font=('Segoe UI', 10), padding=6)

        frame = ttk.Frame(self, padding=24)
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text='Automatização Processo Folha', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Cruze o Ponto com a Escala para achar inconsistências.', style='Sub.TLabel').pack(anchor='w', pady=(4, 20))

        # Ponto
        self.lbl_ponto = ttk.Label(frame, text='Ponto: Não selecionado', wraplength=500, foreground="red")
        self.lbl_ponto.pack(anchor='w', pady=(0, 4))
        ttk.Button(frame, text='1. Escolher Ponto (CSV)', command=self.selecionar_ponto).pack(anchor='w', pady=(0, 16))

        # Escala
        self.lbl_escala = ttk.Label(frame, text='Escala: Não selecionada (Opcional)', wraplength=500, foreground="orange")
        self.lbl_escala.pack(anchor='w', pady=(0, 4))
        ttk.Button(frame, text='2. Escolher Escala (CSV)', command=self.selecionar_escala).pack(anchor='w', pady=(0, 16))

        # Analisar
        ttk.Button(frame, text='3. Analisar Dados', command=self.analisar).pack(anchor='w', pady=(0, 8))

        self.btn_exportar = ttk.Button(frame, text='4. Exportar Excel (.xlsx)', command=self.exportar, state='disabled')
        self.btn_exportar.pack(anchor='w', pady=(0, 16))

        self.lbl_resultado = ttk.Label(frame, text='', wraplength=500)
        self.lbl_resultado.pack(anchor='w', pady=(0, 16))

        botoes_extra = ttk.Frame(frame)
        botoes_extra.pack(anchor='w')

        self.btn_abrir_pasta = ttk.Button(botoes_extra, text='Abrir pasta', command=self.abrir_pasta, state='disabled')
        self.btn_abrir_pasta.pack(side='left', padx=(0, 8))

        self.btn_abrir_excel = ttk.Button(botoes_extra, text='Abrir Excel', command=self.abrir_excel, state='disabled')
        self.btn_abrir_excel.pack(side='left')

    def selecionar_ponto(self):
        caminho = filedialog.askopenfilename(title='Selecione a planilha de PONTO', filetypes=[('CSV', '*.csv')])
        if caminho:
            self.arquivo_ponto = caminho
            self.pasta_saida = os.path.dirname(caminho)
            self.lbl_ponto.config(text=f'Ponto: {os.path.basename(caminho)}', foreground="green")
            self.btn_exportar.config(state='disabled')

    def selecionar_escala(self):
        caminho = filedialog.askopenfilename(title='Selecione a planilha de ESCALA', filetypes=[('CSV', '*.csv')])
        if caminho:
            self.arquivo_escala = caminho
            self.lbl_escala.config(text=f'Escala: {os.path.basename(caminho)}', foreground="green")

    def analisar(self):
        if not self.arquivo_ponto:
            messagebox.showwarning('Atenção', 'Selecione o arquivo de PONTO primeiro.')
            return

        try:
            self.df_erros, self.total_motoristas = analisar_planilha(self.arquivo_ponto, self.arquivo_escala)
            self.lbl_resultado.config(text=f'Análise concluída!\n{self.total_motoristas} motoristas · {len(self.df_erros)} inconsistências.')
            self.btn_exportar.config(state='normal')
        except Exception as e:
            messagebox.showerror('Erro na análise', str(e))

    def exportar(self):
        try:
            self.caminho_xlsx, caminho_csv = exportar_relatorios(self.df_erros, self.pasta_saida)
            self.btn_abrir_pasta.config(state='normal')
            self.btn_abrir_excel.config(state='normal')
            messagebox.showinfo('Pronto!', 'Relatórios gerados com sucesso!')
        except Exception as e:
            messagebox.showerror('Erro ao exportar', str(e))

    def abrir_pasta(self):
        if self.pasta_saida: os.startfile(self.pasta_saida)

    def abrir_excel(self):
        if self.caminho_xlsx: os.startfile(self.caminho_xlsx)

def main():
    app = AppAnalisePonto()
    app.mainloop()

if __name__ == '__main__':
    main()
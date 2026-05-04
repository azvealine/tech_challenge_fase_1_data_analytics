# 📦 Olist Analytics: Diagnóstico Logístico e Motor Preditivo de SLA

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B.svg)
![Pandas](https://img.shields.io/badge/Pandas-Data_Engineering-150458.svg)
![FIAP](https://img.shields.io/badge/FIAP-Tech_Challenge-ED145B.svg)

## 📌 Visão Geral do Projeto
Este repositório contém o pipeline de dados e o painel executivo desenvolvidos para diagnosticar gargalos na malha logística da **Olist** (e-commerce brasileiro). O projeto atua como o trabalho de conclusão (Tech Challenge) para a pós-graduação em Data Analytics da FIAP.

O objetivo principal foi transpor a barreira de relatórios operacionais básicos, construindo um motor de dados focado em **Unit Economics, retenção de clientes (Churn) e eficiência de SLA**. 

Através da engenharia de dados, mapeamos uma anomalia batizada de **"Risco Invisível"**, evidenciando que em mais de 27% das entregas, a companhia consome sua margem de negociação com transportadoras para subsidiar a lentidão na etapa de separação (*picking/packing*) dos lojistas parceiros.

## 🏗️ Arquitetura e Governança de Dados
O pipeline foi construído com foco rigoroso em Data Observability e qualidade da informação (Single Source of Truth):
*   **Ingestão e Saneamento:** Processamento de 8 bases relacionais distintas, com expurgo de anomalias financeiras e tratamento de missing values.
*   **Auditoria de Telemetria:** Isolamento de parceiros logísticos com rastreios corrompidos (sequências temporais invertidas).
*   **Corte Temporal Determinístico:** Ajuste dinâmico de safras (Year-to-Date) para evitar distorções de *Year-over-Year* em painéis C-Level.
*   **LGPD:** Anonimização completa da base, atuando apenas com agregações geográficas macro (sem exposição de PII).

🔗 *Para mais detalhes, acesse a [Documentação Técnica de Governança](documentacao_governanca_dados.md).*

## 📊 Entregáveis
1. **Pipeline de Tratamento (`app_tratamento_dados.py`):** Motor de Feature Engineering e limpeza de ponta a ponta.
2. **Dashboard Executivo (`app_streamlit.py`):** Aplicação interativa em Streamlit contendo Matriz Estratégica Regional, Análise de Churn e diagnóstico de Lead Time.
3. **Relatório Estratégico:** Documento de negócios estruturando as decisões de investimento (Capex/Opex) e roadmap logístico baseado nos achados analíticos.

## 🚀 Como Executar o Projeto Localmente

1. Clone este repositório:
```bash
git clone https://github.com/azvealine/tech_challenge_fase_1_data_analytics.git
cd tech_challenge_fase_1_data_analytics
Instale as dependências necessárias:

Bash
pip install -r requirements.txt
(Certifique-se de ter streamlit, pandas e plotly instalados).

Execute a aplicação Streamlit:

Bash
streamlit run analise/app_streamlit.py
```
👨‍💻 Autor
Aline Azevedo

Data Engineer | Pós-graduando em Data Analytics pela FIAP
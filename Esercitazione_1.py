import pandas as pd
import numpy as np

# =========================================================================
# PARTE 1: IMPORTAZIONE DATI, PROFILI E CALCOLI TOTALI
# =========================================================================

# 1. Caricamento CSV (saltando le prime 10 righe di intestazione PVGIS)
df_pv = pd.read_csv('File_Producibilità_Smart_Grids.csv', skiprows=10, sep=',')
produzione_mensile_kwh = df_pv['E_m'].values[:12]

# 2. Generazione Profili di Carico Mensili (5 Utenti)
# Assumiamo un consumo annuo tra 2500 e 3000 kWh, distribuito con leggeri picchi 
# estivi/invernali per simulare il fabbisogno di climatizzazione.
pesi_mensili = np.array([0.10, 0.09, 0.08, 0.07, 0.07, 0.08, 0.10, 0.10, 0.08, 0.07, 0.07, 0.09])

consumi_utenti = []
for _ in range(5):
    consumo_annuo = np.random.uniform(2500, 3000)
    consumi_utenti.append(consumo_annuo * pesi_mensili)

# Creazione del DataFrame unificato
df_mensile = pd.DataFrame(np.column_stack(consumi_utenti), columns=[f'Utente_{i+1}' for i in range(5)])
df_mensile['Produzione_FV_kWh'] = produzione_mensile_kwh
df_mensile['Somma_Consumi_kWh'] = df_mensile[[f'Utente_{i+1}' for i in range(5)]].sum(axis=1)

# 3. Calcolo Energia Condivisa Mensile
# Ragionamento termodinamico: l'autoconsumo fisico istantaneo viene qui approssimato 
# su base mensile. L'energia scambiabile non può superare la produzione del generatore 
# né il fabbisogno del carico; il surplus viene immesso in rete.
df_mensile['Energia_Condivisa_kWh'] = df_mensile[['Produzione_FV_kWh', 'Somma_Consumi_kWh']].min(axis=1)

# Aggregazione annuale (da kWh a MWh)
energia_condivisa_mwh = df_mensile['Energia_Condivisa_kWh'].sum() / 1000
energia_prodotta_mwh = df_mensile['Produzione_FV_kWh'].sum() / 1000

# 4. Calcoli Economici e Gestionali
# Ragionamento economico: la Tariffa Premio e la Valorizzazione incentivano 
# l'energia condivisa (alleviando la rete), mentre il RID remunera l'energia immessa.
tariffa_premio = energia_condivisa_mwh * 100.0   
valorizzazione = energia_condivisa_mwh * 10.57   
rid = energia_prodotta_mwh * 47.50               

introito_lordo = tariffa_premio + valorizzazione + rid
trattenuta_gestione = introito_lordo * 0.20
introito_netto = introito_lordo - trattenuta_gestione
ripartizione_naif = introito_netto / 5

print("--- PARTE 1: CALCOLI ANNUI ---")
print(f"Energia Condivisa: {energia_condivisa_mwh:.2f} MWh | Energia Prodotta: {energia_prodotta_mwh:.2f} MWh")
print(f"Introito Netto (dopo trattenuta 20%): {introito_netto:.2f} €")
print(f"Ripartizione in 5 parti uguali: {ripartizione_naif:.2f} € per utente\n")


# =========================================================================
# PARTE 2: RIPARTIZIONE AVANZATA (DA STATUTO)
# =========================================================================

capitale_investito = [10000, 7000, 3000, 0, 0]
costo_totale_impianto = 20000

# Quota Fissa Autoconsumo (50% del netto, diviso equamente in 5)
quota_fissa_autoconsumo = (introito_netto * 0.5) / 5

dati_ripartizione = []
for i in range(5):
    # Quota Remunerazione Capitale (50% del netto, proporzionale all'investimento)
    quota_investimento = (introito_netto * 0.5) * (capitale_investito[i] / costo_totale_impianto)
    totale_spettante = quota_fissa_autoconsumo + quota_investimento
    
    dati_ripartizione.append([
        f"Utente {i+1}", 
        capitale_investito[i], 
        round(quota_fissa_autoconsumo, 2), 
        round(quota_investimento, 2), 
        round(totale_spettante, 2)
    ])

df_riassunto = pd.DataFrame(
    dati_ripartizione, 
    columns=['Utente', 'Capitale_Investito_€', 'Quota_Fissa_€', 'Quota_Investimento_€', 'Totale_Spettante_€']
)

print("--- PARTE 2: RIPARTIZIONE AVANZATA ---")
print(df_riassunto.to_string(index=False))

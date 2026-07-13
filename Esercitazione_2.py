import pandas as pd
import numpy as np
import os

# ==========================================
# 1. PARAMETRI DEL SISTEMA E INIZIALIZZAZIONE
# ==========================================
CAPACITA_BATT = 2.5        # kWh
SOC_MIN_PERC = 0.10        # 10%
SOC_MAX_PERC = 0.90        # 90%
P_BATT_MAX = 0.3           # kW (sia carica che scarica)
SOC_INIT = SOC_MIN_PERC    # SOC iniziale al 10%

SOC_MIN_KWH = CAPACITA_BATT * SOC_MIN_PERC
SOC_MAX_KWH = CAPACITA_BATT * SOC_MAX_PERC
SOC_INIT_KWH = CAPACITA_BATT * SOC_INIT

# Tariffe [€/kWh]
TARIFFA_F1 = 0.28
TARIFFA_F2 = 0.20
TARIFFA_F3 = 0.18
PREMIO_DR = 0.30

# ==========================================
# 2. LETTURA E PREPARAZIONE DATI
# ==========================================
def carica_dati():
    """Legge i dati dal file Excel sul Desktop e prepara i profili di carico."""
    percorso_file = os.path.expanduser("~/Desktop/Diagrammi di carico es2.xlsx")
    
    try:
        df = pd.read_excel(percorso_file)
        # Rinomino le colonne per comodità di accesso
        df.columns = ['Ora', 'Carico_kW', 'Generazione_kW', 'Netto_kW']
    except FileNotFoundError:
        print(f"ATTENZIONE: File non trovato in {percorso_file}.")
        print("Genero dati di test basati sulla struttura richiesta per permettere l'esecuzione...")
        df = pd.DataFrame({
            'Ora': range(24),
            'Carico_kW': np.random.uniform(0.5, 2.5, 24),
            'Generazione_kW': [0]*7 + [0.5, 1.2, 2.0, 2.5, 3.0, 2.8, 2.0, 1.5, 0.8, 0.2] + [0]*7
        })
        df['Netto_kW'] = df['Generazione_kW'] - df['Carico_kW']
        
    # Variazione per giorno festivo (es. carico spostato verso le ore centrali, riduzione del 20%)
    df['Carico_Festivo_kW'] = df['Carico_kW'] * 0.8
    
    # Assegnazione fasce orarie feriali
    condizioni_fasce = [
        (df['Ora'].between(8, 18)), # F1: 8:00 - 19:00 (l'ora 18 copre 18:00-18:59)
        (df['Ora'].isin([7, 19, 20, 21, 22])), # F2
        (df['Ora'].isin([23, 0, 1, 2, 3, 4, 5, 6])) # F3
    ]
    df['Prezzo_Feriale'] = np.select(condizioni_fasce, [TARIFFA_F1, TARIFFA_F2, TARIFFA_F3])
    df['Prezzo_Festivo'] = TARIFFA_F3 # Domenica sempre F3
    
    return df

# ==========================================
# 3. LOGICHE DI CONTROLLO BEMS
# ==========================================

def vincola_potenza(p_richiesta, energia_disponibile, limite_potenza=P_BATT_MAX):
    """Calcola la potenza effettiva erogabile rispettando i limiti di inverter e capacità."""
    # Assumendo delta_T = 1 ora, Potenza (kW) = Energia (kWh)
    return min(abs(p_richiesta), limite_potenza, energia_disponibile)

def simula_autoconsumo(df, colonna_carico):
    """PARTE 1: Massimizzazione dell'autoconsumo (logica base)."""
    soc_kwh = SOC_INIT_KWH
    p_batt_array = [] # Positivo: Scarica (aiuta il carico), Negativo: Carica
    
    for _, row in df.iterrows():
        p_net = row['Generazione_kW'] - row[colonna_carico]
        
        if p_net > 0: # Eccesso di produzione -> Carica
            spazio_libero = SOC_MAX_KWH - soc_kwh
            p_carica = vincola_potenza(p_net, spazio_libero)
            soc_kwh += p_carica
            p_batt_array.append(-p_carica)
        else: # Deficit -> Scarica
            energia_estraibile = soc_kwh - SOC_MIN_KWH
            p_scarica = vincola_potenza(abs(p_net), energia_estraibile)
            soc_kwh -= p_scarica
            p_batt_array.append(p_scarica)
            
    # Gestione Vincolo: Integrale nullo nelle 24h (SOC finale = SOC iniziale)
    # Se a fine giornata (ore 21-23) c'è energia in eccesso, forziamo la scarica
    for i in range(21, 24):
        if soc_kwh > SOC_INIT_KWH:
            energia_da_smaltire = soc_kwh - SOC_INIT_KWH
            p_scarica_forzata = vincola_potenza(energia_da_smaltire, energia_da_smaltire)
            p_batt_array[i] += p_scarica_forzata
            soc_kwh -= p_scarica_forzata

    return p_batt_array

def simula_ottimizzazione_costi(df, colonna_carico, colonna_prezzo):
    """PARTE 2: Minimizzazione dei costi."""
    soc_kwh = SOC_INIT_KWH
    p_batt_array = []
    
    for i, row in df.iterrows():
        ora = row['Ora']
        prezzo_attuale = row[colonna_prezzo]
        p_net = row['Generazione_kW'] - row[colonna_carico]
        
        # Logica euristica per feriale: 
        # Carica da rete di notte (F3) se domani non c'è abbastanza FV
        # Scarica in F1/F2 per coprire il carico.
        
        if prezzo_attuale == TARIFFA_F3 and ora < 7:
            # Pre-carica notturna economica
            spazio_libero = SOC_MAX_KWH - soc_kwh
            p_carica = vincola_potenza(P_BATT_MAX, spazio_libero)
            soc_kwh += p_carica
            p_batt_array.append(-p_carica)
            
        elif p_net > 0:
            # Autoconsumo FV standard
            spazio_libero = SOC_MAX_KWH - soc_kwh
            p_carica = vincola_potenza(p_net, spazio_libero)
            soc_kwh += p_carica
            p_batt_array.append(-p_carica)
            
        elif p_net < 0 and prezzo_attuale in [TARIFFA_F1, TARIFFA_F2]:
            # Scarica mirata nelle ore costose
            energia_estraibile = soc_kwh - SOC_MIN_KWH
            p_scarica = vincola_potenza(abs(p_net), energia_estraibile)
            soc_kwh -= p_scarica
            p_batt_array.append(p_scarica)
            
        else:
            p_batt_array.append(0)
            
    # Forzatura integrale nullo a fine giornata (ore 21-23)
    for i in range(21, 24):
        if soc_kwh > SOC_INIT_KWH:
            energia_da_smaltire = soc_kwh - SOC_INIT_KWH
            p_scarica = vincola_potenza(P_BATT_MAX, energia_da_smaltire)
            p_batt_array[i] += p_scarica
            soc_kwh -= p_scarica

    return p_batt_array

def simula_demand_response(df, colonna_carico, colonna_prezzo):
    """PARTE 3: Minimizzazione costi con evento Demand Response (10:00-12:00)."""
    soc_kwh = SOC_INIT_KWH
    p_batt_array = []
    
    for i, row in df.iterrows():
        ora = row['Ora']
        prezzo_attuale = row[colonna_prezzo]
        p_net = row['Generazione_kW'] - row[colonna_carico]
        
        # EVENTO DR (Ore 10 e 11, che coprono il periodo 10:00-12:00)
        if ora in [10, 11]:
            # Priorità assoluta: scaricare al massimo consentito dall'inverter per 
            # contribuire alla riduzione del carico, dato che 0.30 €/kWh > 0.28 €/kWh
            energia_estraibile = soc_kwh - SOC_MIN_KWH
            p_scarica = vincola_potenza(P_BATT_MAX, energia_estraibile)
            soc_kwh -= p_scarica
            p_batt_array.append(p_scarica)
            continue
            
        # Per le altre ore, logica di minimizzazione costi classica
        if prezzo_attuale == TARIFFA_F3 and ora < 7:
            spazio_libero = SOC_MAX_KWH - soc_kwh
            p_carica = vincola_potenza(P_BATT_MAX, spazio_libero)
            soc_kwh += p_carica
            p_batt_array.append(-p_carica)
        elif p_net > 0:
            spazio_libero = SOC_MAX_KWH - soc_kwh
            p_carica = vincola_potenza(p_net, spazio_libero)
            soc_kwh += p_carica
            p_batt_array.append(-p_carica)
        elif p_net < 0 and prezzo_attuale in [TARIFFA_F1, TARIFFA_F2]:
            energia_estraibile = soc_kwh - SOC_MIN_KWH
            p_scarica = vincola_potenza(abs(p_net), energia_estraibile)
            soc_kwh -= p_scarica
            p_batt_array.append(p_scarica)
        else:
            p_batt_array.append(0)

    # Forzatura integrale nullo a fine giornata (ore 21-23)
    for i in range(21, 24):
        if soc_kwh > SOC_INIT_KWH:
            energia_da_smaltire = soc_kwh - SOC_INIT_KWH
            p_scarica = vincola_potenza(P_BATT_MAX, energia_da_smaltire)
            p_batt_array[i] += p_scarica
            soc_kwh -= p_scarica

    return p_batt_array

# ==========================================
# 4. ESECUZIONE SIMULAZIONI
# ==========================================
if __name__ == "__main__":
    df = carica_dati()
    
    # Esecuzione Parte 1
    df['P_Batt_Autoconsumo'] = simula_autoconsumo(df, 'Carico_kW')
    
    # Esecuzione Parte 2
    df['P_Batt_Costi_Feriale'] = simula_ottimizzazione_costi(df, 'Carico_kW', 'Prezzo_Feriale')
    df['P_Batt_Costi_Festivo'] = simula_ottimizzazione_costi(df, 'Carico_Festivo_kW', 'Prezzo_Festivo')
    
    # Esecuzione Parte 3
    df['P_Batt_DR_Feriale'] = simula_demand_response(df, 'Carico_kW', 'Prezzo_Feriale')
    df['P_Batt_DR_Festivo'] = simula_demand_response(df, 'Carico_Festivo_kW', 'Prezzo_Festivo')
    
    print("Simulazione completata con successo. Colonne calcolate:")
    print(df[['Ora', 'P_Batt_Autoconsumo', 'P_Batt_Costi_Feriale', 'P_Batt_DR_Feriale']].head(12))

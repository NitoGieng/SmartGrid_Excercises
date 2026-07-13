# SmartGrid_Excercises
Relazione tecnica di accompagnamento allo Script Python – Esercitazione 1 (CER)

Nella risoluzione di questa esercitazione, ho deciso di impostare lo script Python non come un semplice calcolatore algebrico statico, ma come un vero e proprio modello di simulazione data-driven, applicando alcune logiche tipiche dell'analisi dati per i Building Energy Management System (BEMS). L'obiettivo è stato quello di ottenere un modello aderente alla realtà fisica e facilmente scalabile.

Di seguito i punti chiave dell'architettura del codice:

Acquisizione Dati e Generazione Stocastica dei Carichi: Invece di ipotizzare un'energia condivisa annuale ideale, ho implementato l'importazione diretta del dataset PVGIS tramite pandas, impostando un parsing robusto che ignora l'header testuale del file CSV. Per le utenze, ho utilizzato numpy per sintetizzare i profili di carico dei 5 appartamenti, assegnando consumi randomici (tra 2500 e 3000 kWh annui) distribuiti mensilmente per simulare i picchi stagionali dovuti alla climatizzazione.

Modellazione Termodinamica Mensile: Il cuore dello script è la determinazione dell'energia condivisa. L'ho calcolata applicando rigorosamente il vincolo fisico min(Produzione_FV, Somma_Consumi) per ogni singolo mese. Questo approccio garantisce che l'autoconsumo virtuale rifletta la reale contemporaneità mensile tra generazione e prelievo, restituendo valori di incentivazione (Tariffa Premio e Valorizzazione) molto più realistici rispetto all'applicazione di una percentuale di condivisione fissa.

Scalabilità tramite Calcolo Vettoriale: Per la ripartizione economica descritta nella Parte 2 dell'esercitazione, ho evitato l'approccio "hardcoded" (con variabili separate per ogni utente). Ho inserito i dati di CAPEX in array dedicati. In questo modo, la suddivisione del 50% dell'introito netto per la partecipazione al consumo (Quota Fissa) e del restante 50% per il ritorno sull'investimento (Quota Capitale) avviene tramite operazioni vettoriali. Questo rende il codice altamente scalabile: in caso di espansione della CER a decine di nodi, l'algoritmo non necessita di riscritture strutturali.

Gestione degli Output: Tutti i flussi di cassa elaborati sono stati incapsulati e formattati all'interno di un DataFrame riassuntivo. Questo permette di isolare chiaramente la differenza di rendimento tra chi agisce da prosumer finanziario (Utenti 1, 2 e 3) e chi partecipa unicamente fornendo i propri profili di consumo (Utenti 4 e 5), validando i requisiti normativi dello statuto.

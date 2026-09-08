"""
Server locale che esegue davvero il circuito quantistico del gioco del
quadrato magico di Mermin-Peres (Qiskit) e restituisce il risultato in JSON,
cosicche' la pagina web possa interrogarlo con una semplice fetch().

Avvio:
    pip install -r requirements.txt
    python server.py

Il server resta in ascolto su http://127.0.0.1:5000
Endpoint: GET /gioca  ->  {"riga": 1-3, "colonna": 1-3,
                           "alice1": +-1, "alice2": +-1,
                           "bob1": +-1, "bob2": +-1}
"""

import base64
import io
import os
import random

import matplotlib
matplotlib.use("Agg")  # backend senza interfaccia grafica, necessario su un server
import matplotlib.pyplot as plt

from flask import Flask, jsonify
from flask_cors import CORS
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

app = Flask(__name__)
# CORS aperto: serve per poter chiamare il server da un file .html aperto
# direttamente nel browser (origine "null") o da un altro host/porta.
CORS(app)

simulatore = AerSimulator()


def disegna_circuito_base64(qc):
    """Disegna il circuito con matplotlib e lo restituisce come stringa
    base64 pronta per essere usata in un tag <img src="data:image/png;...">"""
    fig = qc.draw(output="mpl", fold=-1)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    buf.seek(0)
    return "data:image/png;base64," + base64.b64encode(buf.read()).decode("ascii")


def gioca_una_partita():
    """Riproduce esattamente il circuito fornito: due coppie EPR (alice1-bob1
    e alice2-bob2), rotazione dipendente da riga (lato Alice) e colonna
    (lato Bob), misura dei 4 qubit e conversione 0/1 -> +1/-1."""

    q_alice1 = QuantumRegister(1, name="alice1")
    q_alice2 = QuantumRegister(1, name="alice2")
    q_bob1 = QuantumRegister(1, name="bob1")
    q_bob2 = QuantumRegister(1, name="bob2")
    c_misura = ClassicalRegister(4, name="soluzione")
    qc = QuantumCircuit(q_alice1, q_alice2, q_bob1, q_bob2, c_misura)

    # coppie entangled: alice1-bob1 e alice2-bob2
    qc.h(0)
    qc.cx(0, 2)
    qc.h(1)
    qc.cx(1, 3)
    qc.barrier()

    riga = random.randint(1, 3)
    colonna = random.randint(1, 3)

    if riga == 1:
        pass
    elif riga == 2:
        qc.h(0)
        qc.h(1)
    elif riga == 3:
        qc.h(0)
        qc.cx(0, 1)
        qc.h(0)

    if colonna == 1:
        qc.h(2)
    elif colonna == 2:
        qc.h(3)
    elif colonna == 3:
        qc.h(2)
        qc.h(3)
        qc.cx(2, 3)
        qc.h(2)

    qc.measure(q_alice1[0], c_misura[0])
    qc.measure(q_alice2[0], c_misura[1])
    qc.measure(q_bob1[0], c_misura[2])
    qc.measure(q_bob2[0], c_misura[3])

    circuito_immagine = disegna_circuito_base64(qc)

    circuito = transpile(qc, simulatore)
    job = simulatore.run(circuito, shots=1)
    conteggi = job.result().get_counts()

    soluzione = list(conteggi.keys())[0]
    numeri = list(reversed(soluzione))
    for n in range(len(numeri)):
        if numeri[n] == "1":
            numeri[n] = "-1"
        if numeri[n] == "0":
            numeri[n] = "1"

    return {
        "riga": riga,
        "colonna": colonna,
        "alice1": int(numeri[0]),
        "alice2": int(numeri[1]),
        "bob1": int(numeri[2]),
        "bob2": int(numeri[3]),
        "circuito_png": circuito_immagine,
    }


@app.route("/gioca")
def gioca():
    return jsonify(gioca_una_partita())


@app.route("/")
def home():
    return (
        "Server del quadrato magico quantistico attivo. "
        "Usa GET /gioca per estrarre una partita."
    )


if __name__ == "__main__":
    # In locale gira su 127.0.0.1:5000. Su un host come Render, la porta
    # viene indicata dalla variabile d'ambiente PORT.
    porta = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=porta, debug=False)

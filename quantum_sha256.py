import cirq
import numpy as np

# Define quantum functions
def quantum_ch(e, f, g):
    return (e & f) ^ (~e & g)

def quantum_maj(a, b, c):
    return (a & b) ^ (a & c) ^ (b & c)

def quantum_rotate_right(x, n):
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def quantum_sigma0(x):
    return quantum_rotate_right(x, 7) ^ quantum_rotate_right(x, 18) ^ (x >> 3)

def quantum_sigma1(x):
    return quantum_rotate_right(x, 17) ^ quantum_rotate_right(x, 19) ^ (x >> 10)

def quantum_capsigma0(x):
    return quantum_rotate_right(x, 2) ^ quantum_rotate_right(x, 13) ^ quantum_rotate_right(x, 22)

def quantum_capsigma1(x):
    return quantum_rotate_right(x, 6) ^ quantum_rotate_right(x, 11) ^ quantum_rotate_right(x, 25)

def quantum_sha256(message):
    # Initial hash values
    h = [
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    ]

    # Round constants
    k = [
        0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
    ]

    # Preprocessing
    message = bytearray(message.encode())
    ml = len(message) * 8
    message.append(0x80)
    while len(message) % 64 != 56:
        message.append(0x00)
    message += ml.to_bytes(8, 'big')

    # Process the message in 512-bit chunks
    for chunk_start in range(0, len(message), 64):
        chunk = message[chunk_start:chunk_start+64]
        w = [int.from_bytes(chunk[i:i+4], 'big') for i in range(0, 64, 4)]

        # Extend the sixteen 32-bit words into sixty-four 32-bit words
        for i in range(16, 64):
            s0 = quantum_sigma0(w[i-15])
            s1 = quantum_sigma1(w[i-2])
            w.append((w[i-16] + s0 + w[i-7] + s1) & 0xFFFFFFFF)

        # Initialize working variables
        a, b, c, d, e, f, g, h_val = h

        # Main loop
        for i in range(64):
            S1 = quantum_capsigma1(e)
            ch = quantum_ch(e, f, g)
            temp1 = (h_val + S1 + ch + k[i] + w[i]) & 0xFFFFFFFF
            S0 = quantum_capsigma0(a)
            maj = quantum_maj(a, b, c)
            temp2 = (S0 + maj) & 0xFFFFFFFF

            h_val = g
            g = f
            f = e
            e = (d + temp1) & 0xFFFFFFFF
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & 0xFFFFFFFF

        # Update hash values
        h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, [a, b, c, d, e, f, g, h_val])]

    # Convert to binary and measure qubits
    quantum_result = ''.join(f'{x:032b}' for x in h)
    qubits = [cirq.LineQubit(i) for i in range(len(quantum_result))]
    circuit = cirq.Circuit()

    # Apply X gate where the binary result is '1'
    for i, bit in enumerate(quantum_result):
        if bit == '1':
            circuit.append(cirq.X(qubits[i]))

    # Measure all qubits
    circuit.append(cirq.measure(*qubits, key='result'))

    # Simulate the circuit
    simulator = cirq.Simulator()
    result = simulator.run(circuit)

    # Convert the measured result to a classical format
    classical_bits = ''.join(str(bit) for bit in result.measurements['result'][0])
    hex_result = hex(int(classical_bits, 2))[2:].zfill(64)

    return hex_result, quantum_result
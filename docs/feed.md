# Feed C++ — Documentação

O feed é um processo C++20 de alta performance que recebe dados de mercado da B3 via UDP multicast (protocolo UMDF) e os publica via ZMQ para o backend Python.

## Arquivos

| Arquivo | Responsabilidade |
|---------|-----------------|
| `include/umdf_parser.h` | Tipos wire do protocolo UMDF + callbacks |
| `src/umdf_parser.cpp` | Parse de pacotes binários UDP B3 |
| `include/order_book.h` | Estruturas de order book L2 |
| `src/order_book.cpp` | Mantém bids/asks com `std::map`, calcula VWAP/spread/mid |
| `include/step_client.h` | Tipos FIX 4.4 para order entry |
| `src/step_client.cpp` | Sessão TCP FIX com STEP gateway B3 |
| `include/zmq_publisher.h` | Interface do publicador ZMQ |
| `src/zmq_publisher.cpp` | Serializa para JSON e publica em tópicos ZMQ |
| `include/session_manager.h` | Gerencia sessões multicast A e B |
| `src/session_manager.cpp` | Sockets UDP, join multicast, loop de recepção |
| `src/main.cpp` | Entry point, wiring de todos os componentes |

## Protocolo UMDF

A B3 usa UMDF (Unified Market Data Feed) — protocolo binário proprietário baseado em FIX/FAST sobre UDP multicast.

### Estrutura de Pacote

```
PacketHeader (13 bytes)
├── seq_num    : uint32  (big-endian) — sequência para detectar gaps
├── send_time  : uint64  (big-endian) — nanoseconds desde epoch
└── msg_count  : uint8   — número de mensagens no pacote

[msg_count vezes:]
MessageHeader (4 bytes)
├── msg_size   : uint16  — tamanho total incluindo o header
└── msg_type   : char[2] — "W" snapshot, "X" incremental, "d" security def

Corpo da mensagem (variável)
```

### Tipos de Mensagem

| msg_type | Struct | Uso |
|----------|--------|-----|
| `"W"` | `MDSnapshotFullRefresh` | Estado completo do book num momento |
| `"X"` | `MDIncrementalRefresh` + `MDEntry[]` | Atualizações incrementais de preço/quantidade |
| `"d"` | `SecurityDefinition` | Definição de instrumento (símbolo, tipo, vencimento) |

### Codificação de Preços

Todos os preços chegam como `int64` com fator de escala `1e8` (Price8). Conversão:

```cpp
double price = static_cast<double>(raw_price) / 1e8;
```

## Order Book

O `OrderBook` mantém os lados bid e ask como `std::map<double, int64_t>`:

- **Bids**: `std::map<double, int64_t, std::greater<double>>` — decrescente, melhor bid no início
- **Asks**: `std::map<double, int64_t>` — crescente, melhor ask no início

Ações UMDF: `0=New`, `1=Change`, `2=Delete`

```cpp
// Aplicar update
book.apply_bid(price, qty, action);  // action: 0,1=upsert  2=remove
book.apply_ask(price, qty, action);
book.apply_trade(price, qty, aggressor);

// Ler estado
double mid    = book.mid();
double spread = book.spread();
double vwap   = book.vwap();

// Snapshot completo (top 5 levels)
BookSnapshot snap = book.snapshot();
```

## STEP — Order Entry (Opcional)

O `StepClient` implementa uma sessão FIX 4.4 para envio de ordens ao gateway STEP da B3.

```cpp
StepClient client(host, port, sender_comp_id, target_comp_id, password,
    [](const OrderAck& ack) {
        // chamado na thread de recepção para cada ExecutionReport
    });

client.connect();  // envia Logon (35=A)

NewOrderRequest req;
req.cl_ord_id  = "ORD001";
req.symbol     = "PETR4";
req.security_id = 12345;
req.side       = OrderSide::BUY;
req.ord_type   = OrderType::LIMIT;
req.tif        = TimeInForce::DAY;
req.price      = 38.50;
req.qty        = 100;
client.send_new_order(req);

client.send_cancel("ORD001", "PETR4", 100);
client.disconnect();
```

## ZMQ Publisher

Publica dois tópicos em formato JSON:

### `snapshot`

```json
{
  "type": "snapshot",
  "security_id": 12345,
  "symbol": "PETR4",
  "ts": 1716652800000000000,
  "last_px": 38.50,
  "last_qty": 100,
  "vwap": 38.42,
  "total_qty": 4500000,
  "total_val": 172890000.0,
  "bids": [{"price": 38.49, "qty": 500, "orders": 0}, ...],
  "asks": [{"price": 38.51, "qty": 300, "orders": 0}, ...]
}
```

### `trade`

```json
{
  "type": "trade",
  "security_id": 12345,
  "symbol": "PETR4",
  "ts": 1716652800000000000,
  "price": 38.50,
  "qty": 100,
  "aggressor": "B"
}
```

## Build

```bash
sudo apt install cmake libzmq3-dev
cd feed
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

Flags de compilação aplicadas (CMakeLists.txt):
```
-O3 -march=native -mtune=native -funroll-loops -ffast-math
```

## Detecção de Gaps de Sequência

O `UMDFParser` detecta automaticamente gaps no número de sequência e chama o callback configurado:

```cpp
parser.set_gap_callback([](SeqNum expected, SeqNum got) {
    fprintf(stderr, "gap: esperado %u recebido %u\n", expected, got);
    // solicitar retransmissão ao canal de recovery B3
});
```

Canal B (redundância): o `SessionManager` abre sockets separados para os canais A e B. O parser desduplicação por `seq_num` — pacotes repetidos do canal B são simplesmente ignorados.

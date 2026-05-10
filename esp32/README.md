# CardioIA — simulação ESP32 (PlatformIO + Wokwi)

Arquivos principais: `platformio.ini`, `src/main.cpp`, `diagram.json`, `libraries.txt`, `wokwi.toml`.

## Importante: pasta do workspace (evita “não faz nada”)

A extensão **Wokwi** no VS Code/Cursor usa o **`diagram.json` na raiz do workspace**. Abra **esta pasta `esp32` como projeto** (**File → Open Folder → `…/esp32`**), não só a raiz do repositório CardioIA. Se o workspace for a pasta pai, o Wokwi pode gerar outro diagrama (fios errados: DHT sem 3V3/GND, botão no pino errado) e o circuito não bate com o `main.cpp`.

## Onde ver o Serial

A saída de `Serial.print` **não** aparece no painel **TERMINAL** genérico do VS Code. Ela aparece no **Serial Monitor do Wokwi** (painel inferior da simulação). O `diagram.json` está com `"display": "always"` para esse painel abrir junto com a simulação. Baud **115200** (igual ao `Serial.begin` no código).

## VS Code — PlatformIO

1. **File → Open Folder** e escolha a pasta **`esp32`** (é ela que contém o `platformio.ini`).
2. Escolha o ambiente:
   - **`esp32dev`** — gravação na **placa física** (Wi‑Fi = `WIFI_SSID` / `WIFI_PASS` do `secrets.h`).
   - **`esp32dev_wokwi`** — **simulador Wokwi** com MQTT: Wi‑Fi virtual **`Wokwi-GUEST`** (canal 6), não usa o SSID da sua casa.
3. **PROJECT TASKS** → ambiente escolhido → **Build** → **Monitor** (115200).

Para o **Wokwi** carregar o `.bin` certo, o `wokwi.toml` aponta para **`esp32dev_wokwi`**.

A biblioteca **DHTesp** é baixada automaticamente (`lib_deps` no `platformio.ini`).

## VS Code — Wokwi (simulador)

1. Faça pelo menos um **Build** no PlatformIO (gera `.pio/build/esp32dev/firmware.bin`).
2. O arquivo **`wokwi.toml`** já aponta para esse `.bin` / `.elf`.
3. Com a pasta **`esp32`** aberta no VS Code, use **Wokwi: Start Simulator** (extensão Wokwi).

## Wokwi (navegador — wokwi.com)

1. Acesse [novo projeto ESP32](https://wokwi.com/projects/new/esp32).
2. Cole o conteúdo de **`diagram.json`** no diagrama do projeto.
3. No editor de código, **substitua o sketch padrão** pelo conteúdo completo de **`src/main.cpp`** (o site espera um único arquivo estilo Arduino; o código é o mesmo).
4. Em **Library Manager**, adicione **DHTesp** (equivalente ao `libraries.txt`).
5. Simule: **b** / **n** (BPM), **w** (**Wi‑Fi sim** — alterna rede simulada ON/OFF); no **DHT22**, use o painel para temperatura/umidade.
6. Salve e copie o link (**Share**) para o README do repositório e evidências.

## Serial Monitor

Baud **115200**. Com **Wi‑Fi sim** em OFF, a fila enche; ao passar para ON, as amostras saem em **uma linha JSON** (`cardioia.telemetry.v1`) (MQTT e/ou Serial conforme o build).

## Ligações do circuito

No `diagram.json`, o **wokwi-esp32-devkit-v1** usa rótulos **D15** / **D4** / **D5** / **D18** e o UART0 do monitor serial em **TX0** / **RX0** (não `TX` / `RX`). Sem isso o Wokwi ignora as ligações e o Serial fica vazio.

| Sinal    | ESP32   |
|----------|---------|
| DHT22 VCC | 3V3   |
| DHT22 GND | GND   |
| DHT22 dados | GPIO15 (pino **D15** no diagrama) |
| BPM+ (pull-up interno) | GPIO4 (**D4**) + GND |
| BPM− (pull-up interno) | GPIO5 (**D5**) + GND |
| Wi‑Fi sim — toggle online/offline da “rede” | GPIO18 (**D18**) + GND |

Se algum rótulo **GND** falhar na simulação, religue no editor Wokwi a outro GND do devkit.

## MQTT (HiveMQ Cloud) — opcional até você criar `secrets.h`

1. No painel HiveMQ Cloud, crie um cluster, anote **host**, **porta 8883**, usuário e senha (Access Management).
2. Copie `src/secrets.h.example` para **`src/secrets.h`** e preencha `WIFI_*`, `MQTT_*`, `MQTT_TOPIC_TELEMETRY`.
3. **Build** de novo. Com `secrets.h` presente, o firmware tenta Wi-Fi + TLS (`setInsecure()` para simplificar o lab; em produção use CA raiz).
4. Enquanto `wifi_sim` estiver na fase **offline**, nada é drenado. Na fase **online**: se Wi-Fi real não conectar (ex.: Wokwi sem [IoT Gateway](https://docs.wokwi.com/guides/esp32-wifi)), a fila continua sendo mostrada pelo **Serial** para não “sumir” a demo.
5. Não commite `secrets.h` (já está no `.gitignore`).

### Por que o MQTT Explorer ficava vazio no Wokwi?

No simulador, `WiFi.begin("sua rede da casa", …)` **não funciona**: o ESP virtual só enxerga a rede **`Wokwi-GUEST`** (aberta). Sem internet no simulador, o HiveMQ não recebe nada — o firmware então **só imprime JSON no Serial** (espelho).

**O que fazer:**

1. **Build** com ambiente **`esp32dev_wokwi`** (já conecta em `Wokwi-GUEST` + canal 6).
2. Garanta o **Wokwi IoT Gateway** (público costuma bast para HiveMQ na nuvem): [guia Wi‑Fi ESP32](https://docs.wokwi.com/guides/esp32-wifi). No VS Code: **F1** → **Enable Private Wokwi IoT Gateway** se usar o gateway privativo (plano pago).
3. Rode o simulador de novo e veja `MQTT: conectado` no Serial; o Explorer deve listar `cardioia/...`.

**Placa física:** use **`esp32dev`** + `secrets.h` com o SSID/senha reais da sua casa.

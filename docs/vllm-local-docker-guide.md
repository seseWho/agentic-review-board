# Probar Agentic Review Board localmente con vLLM y Docker

Esta guía levanta un servidor vLLM reproducible para ejecutar las pruebas live y
una revisión completa. Todo lo necesario para el servicio está declarado en el
`compose.yaml` del repositorio. El modelo se guarda en un volumen Docker persistente
y no depende de directorios de otro proyecto. Para validar también la interfaz, sigue el
[`runbook de prueba local de la UI`](local-ui-test-runbook.md).

## Configuración incluida

La configuración de referencia está ajustada para una NVIDIA RTX 3060 de 12 GiB:

- imagen: `vllm/vllm-openai:v0.11.0`;
- modelo: `Qwen/Qwen3-4B-AWQ`;
- nombre servido: `qwen3-4b-awq`;
- contexto: 40 960 tokens;
- cuantización: AWQ Marlin;
- puerto local: `127.0.0.1:8000`;
- caché: volumen Docker `agentic-review-board-huggingface-cache` por defecto, o
  el directorio indicado mediante `HF_HOME`;
- configuración de la aplicación: `config/llm.vllm.json`.

El puerto se publica solo en `127.0.0.1`; el servidor no queda expuesto a la red
local. La configuración no contiene credenciales. La primera ejecución descarga
el modelo y la imagen, por lo que necesita conexión a Internet y suficiente
espacio en el almacenamiento de Docker.

### Dónde se guarda el modelo

Sin configurar nada, Compose usa el volumen administrado por Docker
`agentic-review-board-huggingface-cache`. Sus archivos viven dentro del disco de
datos de Docker Desktop y no aparecen como una carpeta normal del repositorio.
Puedes consultar su ubicación lógica con:

```powershell
docker volume inspect agentic-review-board-huggingface-cache
```

Para reutilizar una caché existente del host, define `HF_HOME` antes de arrancar.
En la máquina de referencia:

```powershell
$env:HF_HOME = "D:\_models\huggingface"
docker compose up -d vllm
```

Compose monta entonces `D:\_models\huggingface` en
`/root/.cache/huggingface`. Qwen3-4B-AWQ se reutiliza si ya está presente y los
modelos nuevos se descargan en esa misma ruta. `HF_HOME` solo afecta al comando
actual y a los procesos lanzados desde esa sesión de PowerShell.

Para guardar el ajuste entre sesiones sin versionar una ruta específica de una
máquina, crea un archivo `.env` en la raíz del repositorio:

```dotenv
HF_HOME=D:/_models/huggingface
```

`.env` está ignorado por Git. En otra máquina se puede omitir para usar el
volumen Docker o crear otro `.env` con la ruta local adecuada.

## 1. Requisitos

Se necesita:

1. Python 3.12 o posterior.
2. Docker Desktop con backend WSL 2 en Windows, o Docker Engine en Linux.
3. Docker Compose moderno (`docker compose`).
4. Una GPU NVIDIA compatible y el runtime NVIDIA para contenedores.
5. Al menos 12 GiB de VRAM para la configuración de referencia.

Comprueba las versiones y el acceso a la GPU:

```powershell
python --version
docker version
docker compose version
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu22.04 nvidia-smi
```

En Docker Desktop conviene revisar **Settings > Resources > Advanced > Disk
image location** antes de descargar la imagen. La imagen de vLLM y el modelo
pueden ocupar varias decenas de GB. No ejecutes `docker system prune` sin revisar
antes qué recursos pertenecen a otros proyectos.

## 2. Preparar el proyecto Python

Desde la raíz del repositorio:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

En Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

Verifica primero la suite determinista, que no utiliza red ni modelos:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 3. Evitar conflictos con otros servidores

Solo un proceso puede publicar el puerto 8000. Comprueba si otro contenedor lo
está usando:

```powershell
docker ps --filter publish=8000
```

Si aparece, detenlo desde su propio proyecto o cambia el puerto de este Compose.
Por ejemplo, para publicar en el puerto 8001:

```powershell
$env:VLLM_PORT = "8001"
docker compose up -d vllm
```

En ese caso copia `config/llm.vllm.json` a un archivo `*.local.json` ignorado por
Git y cambia `base_url` a `http://localhost:8001/v1`.

No renombres un contenedor creado por el Compose de otro repositorio: su Compose
puede recrearlo con el nombre original. Este proyecto utiliza su propio servicio
`arb-vllm` y su propio volumen de caché.

## 4. Descargar y arrancar vLLM

```powershell
docker compose pull vllm
docker compose up -d vllm
docker compose ps
docker compose logs -f vllm
```

La primera carga puede tardar bastante porque descarga el modelo, convierte los
kernels AWQ Marlin y reserva la caché KV. Sal del seguimiento de logs con
`Ctrl+C`; el contenedor seguirá ejecutándose.

Cuando `docker compose ps` muestre el servicio como `healthy`, consulta el
catálogo:

```powershell
Invoke-RestMethod http://localhost:8000/v1/models |
  ConvertTo-Json -Depth 6
```

La respuesta debe contener `qwen3-4b-awq` y `max_model_len: 40960`.

También puedes inspeccionar el consumo:

```powershell
docker stats arb-vllm --no-stream
nvidia-smi
```

## 5. Probar el contrato JSON directamente

```powershell
$requestBody = @{
  model = "qwen3-4b-awq"
  messages = @(
    @{
      role = "user"
      content = "Devuelve exclusivamente un objeto JSON con la propiedad status y el valor ok."
    }
  )
  response_format = @{ type = "json_object" }
} | ConvertTo-Json -Depth 6

$response = Invoke-RestMethod `
  -Uri http://localhost:8000/v1/chat/completions `
  -Method Post `
  -ContentType "application/json" `
  -Body $requestBody

$response.choices[0].message.content
```

El contenido esperado es un objeto equivalente a:

```json
{"status":"ok"}
```

## 6. Ejecutar el smoke live de la aplicación

La prueba live exige autorización explícita mediante variable, opción y marcador:

```powershell
$env:ARB_RUN_LIVE_LLM = "1"
$env:ARB_LLM_CONFIG_PATH = (Resolve-Path "config\llm.vllm.json").Path
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe -m pytest `
  -m live_llm `
  --run-live-llm `
  -s
```

El smoke contiene tres comprobaciones:

1. una petición sintética con el contrato estático de Analyst por cada perfil
   seleccionado;
2. una petición Critic mínima construida por la ruta real de Slice 7.1, con su
   catálogo, `oneOf`, valores `const`, sección dinámica delimitada y
   `response_format` dinámico.
3. una petición Risk Reviewer mínima construida por la ruta real de Slice 7.2,
   con `oneOf`, `const`, `minItems`, `maxItems` y el ámbito dinámico exacto.

Las dos pruebas dinámicas demuestran que el servidor acepta el subconjunto JSON
Schema utilizado por Slice 7.1 y Slice 7.2 y devuelve objetos JSON directos. No
demuestran calidad semántica ni sustituyen la validación de los participantes.

Resultado de compatibilidad validado con vLLM 0.11.0 en la RTX 3060 de
referencia:

```text
live LLM profile: local-qwen3
live dynamic Critic profile: local-qwen3
live dynamic Risk Reviewer profile: local-qwen3
1 failed, 2 passed
```

Los dos contratos dinámicos fueron aceptados y completados. La comprobación
estática falló por contenido del modelo que no superó la validación de la
aplicación, no por rechazo del JSON Schema en vLLM. Por tanto, este resultado
valida la compatibilidad del proveedor con los esquemas dinámicos, pero no la
fiabilidad semántica de Qwen3-4B-AWQ.

Si alguna prueba dinámica falla porque vLLM rechaza `oneOf`, `const`, `minItems`
o `maxItems`, conserva el
error como evidencia y detén la evaluación. No cambies a `JSON_OBJECT`, no
debilites el esquema y no repitas hasta obtener éxito.

El smoke mínimo puede pasar aunque un escenario grande exceda el contexto. En ese
caso los logs de vLLM muestran los tokens solicitados y el límite configurado. No
trunques el catálogo ni retires el esquema delimitado: detén la campaña y utiliza
posteriormente un perfil/modelo con contexto explícitamente suficiente.

## 7. Ejecutar una revisión completa

Empieza con el escenario inglés, que facilita comparar resultados con las
pruebas de referencia:

```powershell
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\critical-desktop-migration.en.json `
  --output artifacts\critical-desktop-migration.en.local.json
```

Para conservar cada respuesta sin validar y diagnosticar un fallo contractual:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_review.py `
  --config config\llm.vllm.json `
  --input examples\reviews\critical-desktop-migration.en.json `
  --output artifacts\critical-desktop-migration.en.diagnostic.json `
  --raw-output-dir artifacts\critical-desktop-migration.en.raw
```

`artifacts/` está ignorado por Git. Las salidas crudas pueden incluir datos
sensibles del caso revisado; úsalas solo para diagnóstico.

El runner siempre intenta guardar el agregado de confianza. Devuelve código 0
si la revisión queda `COMPLETED` y código 1 si queda `INCOMPLETE`. Un código 1
puede significar que vLLM respondió correctamente pero el modelo incumplió un
contrato semántico.

## 8. Resultado de referencia y criterio previo a la interfaz

Validación del 29 de agosto de 2026 con RTX 3060 12 GiB:

- suite determinista: 1 038 pruebas superadas y 1 omitida;
- smoke vLLM: superado;
- Analyst: completado;
- Solution Architect: completado;
- Risk Reviewer: completado;
- Critic: rechazado por validación de salida;
- Coordinator: pendiente por diseño fail-closed;
- duración end-to-end: 212,26 segundos.

El Critic produjo JSON estructuralmente válido, pero mezcló referencias, por
ejemplo `PROBLEM_ANALYSIS / ALTERNATIVE_ASSUMPTION / ALT-001`, cuando esa
referencia pertenece a `SOLUTION_ALTERNATIVES`. Qwen3-8B-AWQ sirve para validar
la integración y los estados de error, pero no ha demostrado fiabilidad
semántica suficiente para completar siempre los cinco participantes.

Antes de construir la interfaz deberían quedar comprobados estos comportamientos:

1. El smoke live es estable.
2. Una revisión completa o incompleta se persiste correctamente.
3. Los estados `COMPLETED`, `FAILED` y `PENDING` se distinguen claramente.
4. Los fallos contractuales no activan silenciosamente etapas dependientes.
5. Se decide si el producto necesita esquemas dinámicos, reintentos acotados o
   un modelo más capaz para los roles más exigentes.

### Evaluación de Slice 7.1

Slice 7.1 exige exactamente cinco invocaciones independientes del mismo escenario,
sin retry automático, sustitución ni borrado selectivo. Usa rutas diferentes:

```powershell
1..5 | ForEach-Object {
  $run = $_.ToString("00")
  .\.venv\Scripts\python.exe scripts\run_live_review.py `
    --config config\llm.vllm.json `
    --input examples\reviews\critical-desktop-migration.en.json `
    --output "artifacts\slice-7.1-run-$run.json" `
    --raw-output-dir "artifacts\slice-7.1-run-$run.raw"
}
```

PowerShell continúa el bucle aunque una ejecución devuelva código 1. No vuelvas a
ejecutar solo los números fallidos. Registra los cinco resultados, configuración,
imagen, GPU y tiempos en
`specs/007.1-dynamic-critic-schema/live-evaluation.md`. Los archivos bajo
`artifacts/` permanecen ignorados y pueden contener información sensible.

Con el escenario de referencia actual, la petición Critic dinámica observada
necesita 34 227 tokens (30 131 de mensajes y 4 096 de salida). Por eso el
compose usa 40 960; el perfil histórico de 16 384 sólo servía para el smoke
mínimo y no para esta revisión completa.

## 9. Operación diaria

Arrancar y esperar a que esté listo:

```powershell
docker compose up -d vllm
docker compose ps
```

Ver logs:

```powershell
docker compose logs -f vllm
```

Parar conservando modelo e imagen:

```powershell
docker compose down
```

Actualizar solo la imagen configurada:

```powershell
docker compose pull vllm
docker compose up -d vllm
```

## 10. Recuperar espacio

`docker compose down` no borra el modelo. Para ver el volumen:

```powershell
docker volume inspect agentic-review-board-huggingface-cache
```

Para borrar también la caché del modelo hay que solicitarlo explícitamente:

```powershell
docker compose down --volumes
```

Ese último comando obliga a descargar de nuevo el modelo en el próximo arranque.
No lo uses si quieres conservar la caché.

## Ajustes para otras GPU

Los valores pueden modificarse temporalmente sin editar `compose.yaml`:

```powershell
$env:VLLM_MAX_MODEL_LEN = "8192"
$env:VLLM_GPU_MEMORY_UTILIZATION = "0.90"
$env:VLLM_KV_CACHE_DTYPE = "auto"
docker compose up -d vllm
```

Si la carga falla por falta de VRAM, reduce primero `VLLM_MAX_MODEL_LEN` a
`12288` y después a `8192`. Mantén `max-num-seqs=1`, ya que el flujo actual es
secuencial. Cambiar el repositorio o el nombre servido del modelo exige mantener
sincronizados `VLLM_MODEL`, `VLLM_SERVED_MODEL_NAME` y el campo `model` de la
configuración JSON de la aplicación.

Para ejecutar el escenario completo del Slice 7.1 hacen falta al menos 34.227
tokens entre entrada y salida. La configuración de referencia usa
`Qwen/Qwen3-4B-AWQ`, 40.960 tokens y caché KV `auto`; no necesita FP8,
FlashInfer ni offload en la RTX 3060 de 12 GiB.

La investigación con el modelo 8B se conserva como contexto de diagnóstico:
vLLM 0.8.5 sólo disponía de 2,96 GiB para KV frente a los 5,62 GiB necesarios;
FP8 E5M2 forzaba el motor V0 y excedía el timeout al compilar el esquema
dinámico; el offload V1 requería UVA, no disponible bajo WSL; y vLLM 0.11.0
encontró incompatibilidades de kernel FP8 en Ampere. Estas combinaciones no son
la configuración soportada del proyecto.

Si se cambia de modelo o GPU, conserva siempre suficiente contexto para la suma
de prompt y salida. No reduzcas el esquema, trunques el catálogo ni sustituyas
ejecuciones fallidas para hacer pasar la evaluación.

# Runbook de prueba local de la UI

Este runbook permite validar la interfaz pedagógica de Agentic Review Board en Windows con
PowerShell. Incluye una ejecución determinista sin modelo y una ejecución integral con la
configuración de referencia para vLLM y una NVIDIA RTX 3060 de 12 GiB.

Ejecuta todos los comandos desde la raíz del repositorio. La ruta esperada en la máquina de
referencia es:

```powershell
Set-Location "D:\DEVELOP\GitHub\SeseWho\agentic-review-board"
```

## Qué valida cada recorrido

| Recorrido | Modelo real | GPU | Propósito |
|---|---:|---:|---|
| Suite automatizada | No | No | Regresión del dominio, agentes, orquestación y UI |
| UI determinista | No | No | Formulario, estados, detalle de agentes y resultado final |
| UI de producción | Sí | Sí | Integración completa del navegador con los cinco agentes y vLLM |

La UI determinista no sustituye la prueba de producción. La prueba de producción tampoco
demuestra por sí sola que el modelo vaya a cumplir siempre los contratos semánticos.

## 1. Requisitos previos

- Python 3.12 o posterior.
- Dependencias del proyecto instaladas en `.venv`.
- Docker Desktop con WSL 2 para la prueba real.
- Driver NVIDIA y acceso de Docker a la GPU.
- Puerto 8501 libre para Streamlit.
- Puerto 8000 libre para vLLM.
- Espacio suficiente en Docker para la imagen y el modelo.

Comprueba el entorno:

```powershell
py -3.12 --version
docker version
docker compose version
nvidia-smi
Test-Path .\.venv\Scripts\python.exe
```

Si todavía no existe el entorno Python:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Si `.venv` existe pero su intérprete ya no arranca después de actualizar Python, conserva el
directorio para diagnóstico, crea un entorno nuevo y vuelve a instalar el proyecto. No borres
el entorno anterior hasta comprobar el reemplazo.

## 2. Verificación automatizada previa

Ejecuta primero las pruebas que no utilizan red, Docker ni modelos:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m mypy .
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pip check
```

Criterio de paso:

- no hay pruebas fallidas ni errores;
- las pruebas live se omiten mientras no se autoricen explícitamente;
- mypy y Ruff terminan con código 0;
- `pip check` no encuentra dependencias incompatibles.

La línea base aceptada más reciente está registrada en
[`../specs/008-pedagogical-ui/acceptance.md`](../specs/008-pedagogical-ui/acceptance.md).

## 3. Recorrido rápido de la UI sin modelo

Arranca la composición determinista usada por las pruebas funcionales:

```powershell
.\.venv\Scripts\python.exe -m streamlit run `
  tests\ui\fixtures\deterministic_streamlit_app.py `
  --server.address localhost `
  --server.port 8501
```

Abre <http://localhost:8501>. Si Streamlit no abre el navegador automáticamente, copia esa
dirección manualmente.

Realiza el recorrido:

1. Comprueba que aparecen seis campos y las cinco tarjetas del proceso.
2. Escribe una descripción no vacía; los otros campos son opcionales.
3. Pulsa una sola vez **Start Review**.
4. Espera al estado global **Completed**.
5. Abre el detalle de cada participante.
6. Comprueba que aparece la sección independiente **Final result**.
7. Pulsa **New Review** y verifica que se limpian formulario, estados y resultado.

El orden visible debe ser Analyst, Solution Architect, Risk Reviewer, Critic y Coordinator.
Cada participante completado debe tener un artefacto confiable. Detén Streamlit con `Ctrl+C`.

## 4. Arrancar vLLM para la prueba real

La configuración versionada utiliza:

- `vllm/vllm-openai:v0.11.0`;
- `Qwen/Qwen3-4B-AWQ` servido como `qwen3-4b-awq`;
- cuantización AWQ Marlin y FP16;
- contexto de 40 960 tokens;
- una sola secuencia concurrente;
- puerto local `127.0.0.1:8000`.

Comprueba primero que ningún otro servicio utiliza el puerto:

```powershell
docker ps --filter publish=8000
```

Arranca el servicio declarado por el repositorio:

```powershell
docker compose config
docker compose up -d vllm
docker compose ps
docker compose logs -f vllm
```

La primera ejecución puede descargar varios gigabytes y tardar bastante. Cuando los logs
indiquen que la aplicación está preparada, sal del seguimiento con `Ctrl+C`; esto no detiene
el contenedor.

Comprueba su estado y catálogo:

```powershell
docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' arb-vllm

Invoke-RestMethod http://localhost:8000/v1/models |
  ConvertTo-Json -Depth 6
```

El contenedor debe estar `healthy` y el catálogo debe contener `qwen3-4b-awq`. Si existe un
proxy de sistema, `localhost` y `127.0.0.1` deben quedar excluidos.

## 5. Ejecutar la UI de producción

En una terminal distinta a la de Docker:

```powershell
$env:ARB_LLM_CONFIG_PATH = (Resolve-Path ".\config\llm.vllm.json").Path
$env:NO_PROXY = "localhost,127.0.0.1"

.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py `
  --server.address localhost `
  --server.port 8501
```

Abre <http://localhost:8501>. Cargar la página no llama al modelo; la ejecución comienza
únicamente al pulsar **Start Review**.

Usa como entrada de referencia
[`../examples/reviews/critical-desktop-migration.en.json`](../examples/reviews/critical-desktop-migration.en.json).
Para consultar sus valores cómodamente:

```powershell
$scenario = Get-Content `
  ".\examples\reviews\critical-desktop-migration.en.json" `
  -Raw | ConvertFrom-Json

$scenario | Format-List
$scenario.constraints
$scenario.context
$scenario.stated_facts
```

Copia `title`, `description` y `objective` en sus campos. Copia cada elemento de
`constraints`, `context` y `stated_facts` en una línea distinta de su área correspondiente.

Antes de empezar:

- confirma que los cinco agentes están en estado **Pending**;
- anota la hora de inicio;
- pulsa **Start Review** una sola vez;
- no recargues ni cierres la pestaña mientras se ejecuta.

La ejecución de referencia tarda aproximadamente dos minutos, aunque una carga fría puede
tardar más. El flujo es secuencial y no realiza retry, fallback, reparación de salida ni
cambio automático de modelo.

## 6. Criterios de aceptación manual

Una ejecución completa pasa cuando:

- el estado global termina en **Completed**;
- los cinco agentes terminan en **Completed** y en el orden canónico;
- cada etapa completada muestra su artefacto confiable;
- Coordinator produce la sección **Final result**;
- el resultado conserva riesgos, incertidumbres y estado de la evidencia;
- la UI no muestra prompts, respuestas crudas, credenciales ni detalles internos de errores.

Una ejecución **Incomplete** también puede ser una observación válida del modelo. En ese
caso comprueba que:

- la etapa que incumple el contrato termina en **Failed** y no presenta salida confiable;
- las etapas anteriores siguen siendo inspeccionables;
- las etapas posteriores obligatorias figuran como no ejecutadas;
- no aparece un resultado final inventado;
- se conserva la ejecución fallida sin repetir únicamente la etapa problemática.

## 7. Evidencia mínima que debe registrarse

Para que una ejecución sea reproducible, anota:

```powershell
git rev-parse HEAD
docker compose images
docker compose ps
nvidia-smi
```

Registra además:

- fecha y hora;
- escenario utilizado;
- versión de vLLM, imagen, modelo y configuración;
- GPU, VRAM y versión del driver;
- duración aproximada;
- estado final de Review y de cada agente;
- presencia o ausencia de **Final result**;
- mensaje público mostrado por la UI si existe un fallo.

No registres claves, prompts internos ni respuestas crudas salvo que exista una necesidad de
diagnóstico explícita. Los archivos de `artifacts/` están ignorados por Git, pero pueden
contener información sensible.

## 8. Diagnóstico rápido

### Streamlit no arranca

Comprueba el intérprete y la instalación:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show streamlit
.\.venv\Scripts\python.exe -m pip check
```

### El puerto 8501 está ocupado

```powershell
Get-NetTCPConnection -LocalPort 8501 -State Listen
```

Detén la instancia anterior o arranca Streamlit con otro puerto, por ejemplo 8502, y abre la
URL correspondiente.

### vLLM no llega a `healthy`

```powershell
docker compose ps
docker compose logs --tail 200 vllm
docker stats arb-vllm --no-stream
nvidia-smi
```

Busca falta de VRAM, descarga incompleta, error del runtime NVIDIA o conflicto de puerto. La
revisión de referencia necesita el contexto configurado de 40 960 tokens; reducirlo puede
permitir un smoke pequeño, pero deja de validar el escenario completo.

### La UI no conecta con vLLM

```powershell
$env:ARB_LLM_CONFIG_PATH
$env:NO_PROXY
Invoke-RestMethod http://localhost:8000/v1/models
```

Confirma que `ARB_LLM_CONFIG_PATH` apunta a un archivo existente y que el nombre servido por
vLLM coincide con `qwen3-4b-awq` en `config/llm.vllm.json`.

### Un agente falla aunque vLLM responda

Esto normalmente indica que la salida del modelo incumplió un contrato estructural o
semántico. Conserva el estado **Incomplete**, los estados de cada etapa y los logs. No cambies
silenciosamente a `JSON_OBJECT`, no debilites el esquema y no repitas hasta obtener un éxito.

## 9. Apagado seguro

Detén Streamlit con `Ctrl+C` en su terminal. Después detén el servicio conservando la imagen
y la caché del modelo:

```powershell
docker compose down
```

Comprueba que no quedan procesos del runbook:

```powershell
docker compose ps
Get-NetTCPConnection -LocalPort 8501,8000 -State Listen -ErrorAction SilentlyContinue
```

No uses `docker compose down --volumes` ni `docker system prune`: ambos pueden eliminar datos
que resulta costoso volver a descargar.

## Referencias

- [Guía de vLLM y Docker](vllm-local-docker-guide.md)
- [Aceptación determinista y live del Slice 8](../specs/008-pedagogical-ui/acceptance.md)
- [Escenarios de referencia](../examples/reviews/README.md)
- [Configuración local de vLLM](../config/llm.vllm.json)

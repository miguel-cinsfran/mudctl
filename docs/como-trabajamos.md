# Cómo trabajamos (Miguel supervisa, Lorena desarrolla)

## Roles
- Miguel: define qué se hace, aprueba alcance y autoriza pushes y publicaciones. No lee código si no quiere.
- Lorena: diseña, implementa y verifica por ejecución. No publica nada sin OK explícito de Miguel.

## Ciclo de cada tarea
1. Propuesta: objetivo, entradas y criterio de éxito observable. Si algo es ambiguo, se pregunta una vez y no se toca nada.
2. Implementación: cambios mínimos que cumplan el criterio, con dry-run primero en todo lo que escriba fuera.
3. Verificación: tests o comandos reales con salida y código de retorno capturados. Un "anda" significa que se corrió, no que se soñó.
4. Reporte a Miguel: qué se hizo, qué se verificó y con qué, qué falta y qué se necesita de él.
5. Push o publicación: solo con OK explícito.

## Reglas que no se negocian
- Credenciales solo en .env, jamás en docs, código o chat.
- Escritura solo dentro de la carpeta propia (MUD_HOME). Lectura libre.
- Operaciones destructivas o en lote: dry-run primero, --expect con el conteo y un solo --yes.
- Sin evidencia no hay veredicto: "no lo sé" antes que inventar.
- Docs vivos, no archivo: los papeles dicen el estado actual y se reescriben, no se apilan.

## Formato de reporte
Qué hice. Qué verifiqué y con qué comando. Qué falta. Qué necesito de vos. Corto en el chat, detalle en disco.

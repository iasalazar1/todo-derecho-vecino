Bitácora — Todo Derecho Vecino
Ruta de trabajo (v4) — fases del proyecto

Acordada al retomar el repo todo-derecho-vecino como línea base. Código antes que AWS: el preprocesamiento y la FSM de WhatsApp no dependen de infraestructura en la nube y provisionar Aurora/Fargate antes de tener el corpus y el esquema validados arriesga tener que rehacer la infraestructura a medias.

Fase	Foco	Qué se hace	Depende de AWS	Estado
0. Preparación	—	Revisión manual de OCR (_reviewed.txt); en paralelo, iniciar verificación del número de WhatsApp Business en Meta	No	✅ Completada
1. Preprocesamiento — orquestador y chunking	Preprocesamiento	legal_document_processor.py: chunking por artículo/fracción, enriquecido con autoridad_ner.py y procedimiento_ner.py, esquema de metadatos completo	No	✅ Completada (18/20 documentos sólidos; PDDU/PPCU pendientes de limpieza manual)
2. RAG local (sin Bedrock ni Aurora)	Preprocesamiento	Cargar los JSON de chunks en un vector store local, validar retrieval + cita exacta, iterar el prompt de generación con la API de Claude directamente	No	🔵 En curso
3. Integración WhatsApp — FSM	WhatsApp	Adaptar la FSM de AgentesMX (estados, validators.py, router.py) al dominio legal; migrar el canal de Twilio a Meta Cloud API; correr local con ngrok	No	⬜ Pendiente
4. Entorno AWS	Infraestructura	Terraform (red, IAM, Aurora Serverless v2 + pgvector con el esquema ya validado, Fargate), CI/CD, migración de embeddings del vector store local a pgvector	Sí	⬜ Pendiente
5. Corte a producción	Infraestructura	Multi-AZ, monitoreo con alertas, simulacro de failover, mx-central-1, AWS Budgets	Sí	⬜ Pendiente
Completado
legal_document_processor.py construido y validado contra el corpus real (no contra datos de prueba):
Chunking por artículo/fracción para leyes y reglamentos, con metadatos (título/capítulo/sección, cita_legal, fechas de publicación/reforma extraídas del propio texto).
Tres correcciones al regex de detección de artículos, cada una encontrada probando contra texto real, no a priori:
El patrón capturaba referencias cruzadas dentro del texto ("de conformidad con el artículo 11...") — se corrigió exigiendo puntuación de cierre inmediata después del número.
Algunos documentos usan "ARTÍCULO" en mayúsculas — se hizo insensible a mayúsculas/minúsculas.
Algunos documentos usan "Artículo N." (solo punto) en vez de "Artículo N .-" (con guion) — se quitó la exigencia del guion y en su lugar se añadió validación de secuencia ascendente para seguir filtrando referencias cruzadas.
Modo de lote (--batch documentos_config.json) para procesar todo el corpus con un solo comando, saltando sin error los documentos que aún no tienen _reviewed.txt.
Rama especializada para Programas de Desarrollo Urbano (PDDU/PPCU), que no usan "Artículo N." sino secciones numeradas con decimales (4.3.1, 4.4.2...); incluye limpieza de bloques de índice interno que interferían con la detección de secciones.
18 de 20 documentos del corpus procesados con resultados sólidos: ~7,200+ fragmentos generados entre leyes y reglamentos, cada uno con cita_legal verificable.
documentos_config.json armado y depurado: 20 documentos, con corrección de varios nombres de archivo que no coincidían entre el config y el disco (acentos, espacios, versiones de documento distintas a las anotadas originalmente).
Pendiente
 Completar las URLs reales de la Gaceta Oficial en documentos_config.json — los 20 documentos siguen con "fuente": "PENDIENTE: URL de la Gaceta Oficial". Buscar en data.consejeria.cdmx.gob.mx.
 Limpiar manualmente los bloques de índice duplicados en PPCU Hipódromo — se detectó que la numeración de secciones (1.1 a 8.4) aparece repetida en al menos tres pasadas distintas dentro del mismo documento, lo que confunde el chunker automático. Revisar durante la pasada de OCR y eliminar los bloques de índice que no tengan desarrollo de contenido real debajo.
 Regenerar el JSON de PDDU-Cuauhtémoc con el título correcto — se procesó por error con --titulo "Programa Parcial de Desarrollo Urbano Hipódromo" (el título de PPCU, no el suyo).
 Confirmar que las versiones de dos documentos son las correctas, no un desfase accidental de descarga:
Ley Orgánica de Alcaldías: el config original decía v6.1, el archivo real es v6.4.
Reglamento de la Ley de Establecimientos Mercantiles: el config original decía v2, el archivo real es v1.
 Validar autoridad_ner.py (spaCy + es_core_news_sm) en el entorno local — no se pudo probar en el entorno de Claude; confirmar que sujetos_obligados se llena correctamente al correr el pipeline completo.
 Afinar la heurística de tipo_disposicion — actualmente casi el 100% de los fragmentos del corpus quedan marcados needs_review: true; conviene revisar ejemplos reales de varias leyes para mejorar las reglas léxicas.
 Revisión manual de calidad: inspeccionar una muestra de chunks de cada documento contra el PDF original, con prioridad en PDDU/PPCU (mayor tasa de error esperada que en las leyes).
 Fase 2 del roadmap: motor RAG local (retrieval + generación con citas) sobre los 18 documentos ya validados, antes de tocar infraestructura de AWS.
Decisiones tomadas
documentos_config.json se mantiene con solo 4-5 campos por documento (reviewed_path, titulo, fuente, tipo_documento, y opcionalmente autoridad_principal). Se decidió no agregar palabras clave, autoridades ni procedimientos a nivel de documento completo: esa información varía por artículo/fracción, no por ley, y ya está contemplada como salida automática por fragmento dentro de legal_document_processor.py (tema_principal, sujetos_obligados, tipo_disposicion). Agregarla al config duplicaría trabajo manual en un nivel de detalle menos útil que el automático.

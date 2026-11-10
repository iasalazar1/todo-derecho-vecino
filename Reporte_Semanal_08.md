# Reporte semanal 08 — Frontend web

**Proyecto:** Todo Derecho Vecino — MVP de estancia INFOTEC–CENIDET  
**Semana:** 8 — Frontend web  
**Fecha de cierre:** 9 de noviembre de 2026  
**Rama:** `mvp-estancia`

## Qué se hizo

Se construyó y publicó la interfaz web estática del MVP y se conectó con el endpoint `POST /consulta` de API Gateway. El usuario confirmó que una consulta desde el dominio público de CloudFront produjo una respuesta correcta y similar a la obtenida desde el servidor local.

## Cómo se hizo

### Frontend
Se utilizaron HTML, CSS y JavaScript estáticos, sin framework. Se publicaron `index.html`, `styles.css`, `script.js` y `config.js` en S3.

### S3 y CloudFront
El frontend se cargó al bucket privado `todo-derecho-vecino-frontend-857385469837-us-east-1`. CloudFront utiliza Origin Access Control (OAC) para leer el bucket, sin habilitar acceso público directo.

- Distribución: `E34XFAO1L3C0JJ`.
- Dominio: `d3oqt1m39hvkdh.cloudfront.net`.
- URL: https://d3oqt1m39hvkdh.cloudfront.net
- Estado observado: `Deployed`, habilitada.

El despliegue de `terraform/base` terminó con `Apply complete! Resources: 8 added, 1 changed, 0 destroyed.`

### CORS de API Gateway
Se modificó `terraform/dev/api_gateway.tf` para permitir el origen CloudFront, conservando `http://localhost:5500`. Se mantuvieron los métodos `POST` y `OPTIONS`, el encabezado `content-type` y `max_age = 300`. Se ejecutaron `terraform fmt`, `terraform validate` y `terraform plan`. Tras la autorización del usuario, el apply terminó con `Apply complete! Resources: 0 added, 1 changed, 0 destroyed.`

## Problemas identificados y resolución

El navegador público requería que API Gateway autorizara explícitamente el origen de CloudFront. Se agregó el dominio HTTPS a `allow_origins` mediante Terraform. No fue necesario modificar el contrato del backend.

## Evidencia / entregable

- Frontend: https://d3oqt1m39hvkdh.cloudfront.net
- API: `https://1zhgtujka8.execute-api.us-east-1.amazonaws.com/consulta`
- Distribución: `E34XFAO1L3C0JJ`, estado `Deployed`.
- Bucket: `todo-derecho-vecino-frontend-857385469837-us-east-1`.
- CORS aplicado: un recurso modificado, ninguno creado o destruido.
- Prueba pública confirmada por el usuario.

## Estado frente al cronograma

**Semana 8 completada.** El flujo web público está funcional en el caso probado. Esta prueba no constituye una evaluación global de calidad del retriever ni una validación jurídica de las respuestas.

## Limitaciones y continuidad

- La API permanece sin autenticación; es una limitación del MVP y debe revisarse en Semana 9.
- No se ha confirmado que las consultas espontáneas queden almacenadas como dataset histórico de evaluación.
- Las fuentes conservan `needs_review = true` / `pendiente_revision = true`; la prueba técnica no sustituye revisión jurídica de vigencia, aplicabilidad y exactitud.
- El estado de apagado de DEV debe verificarse con `./terraform/dev-status.sh`; no se infiere del despliegue del frontend.
- `terraform/dev-down.sh` no elimina los recursos persistentes del frontend en `terraform/base`.

## Pendientes para Semana 9

1. Pruebas E2E con casos válidos, evidencia insuficiente y errores técnicos.
2. Revisión IAM con principio de mínimo privilegio.
3. Verificación y activación de logs básicos de CloudWatch.
4. Revisión del throttling de API Gateway.
5. Decisión sobre autenticación o aceptación documentada de la limitación.
6. Inspección de los datos de consultas registrados actualmente; separar logs operativos de un dataset de evaluación.
7. Conjunto fijo/versionado de preguntas y medición del retriever con `Precision@k` / `Recall@k`; evaluación humana separada de respuestas y citas.
8. Política mínima de privacidad, acceso y retención antes de registrar consultas reales.

Subir el reporte a Drive: https://drive.google.com/drive/folders/1-f1tkBKLP7c8aZo-IU9_Zb3ME4CEIB9K

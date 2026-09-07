# mudctl — Documentación de Investigación

## Protocolo del puerto 3008

### Contexto
El servidor FTP de Reinos de Leyenda usa el puerto 3008, que no es el puerto FTP estándar (21), ni el puerto SFTP (22) o FTPS (990).

### Análisis

El puerto 3008 corresponde a un servidor FTP personalizado, no un puerto de servicio estándar asignado por IANA. Los puertos FTP comunes son:
- 21: FTP estándar (control)
- 22: SFTP (SSH File Transfer Protocol)
- 990: FTPS explícito (SSL/TLS)
- 2121: FTP alternativo

El puerto 3008 sugiere que es un servidor FTP dedicado de Reinos de Leyenda, posiblemente un servidor Pure-FTPd o ProFTPD configurado para escuchar en un puerto no estándar por razones de seguridad o redirección de puertos.

### Verificación de seguridad

- Conexión: `ftp reinosdeleyenda.es 3008` funciona (se observa en las credenciales de Mordisco)
- Autenticación: usuario `hazrakh` con contraseña almacenada en `.env`
- Protocolo: FTP plano (no se observa indicación de TLS/SSL en las credenciales compartidas)

### Riesgos de seguridad identificados

1. **Contraseña en texto plano**: Las credenciales se transmiten sin cifrado. Si alguien intercepta el tráfico, obtiene acceso completo.
2. **Puerto no estándar**: No mejora la seguridad real, solo añade obscuridad.
3. **Sin 2FA**: No se observa autenticación de dos factores.

### Recomendaciones

1. **Cambiar contraseña periódicamente**: Cada 90 días o si se sospecha compromiso.
2. **Contactar a Mordisco**: Confirmar que el acceso sigue activo para un inmortal de rango bajo.
3. **Usar `.env` para credenciales**: Nunca pasar contraseñas por CLI ni hardcodearlas.
4. **Revisar si hay SFTP disponible**: Muchos servidores FTP modernos ofrecen SFTP en el mismo puerto o uno adyacente.
5. **Monitorear actividad**: Si el acceso es para un bot/agente, revisar logs periódicamente.

### Comandos de prueba manual

```bash
# Conectar interactivamente
ftp reinosdeleyenda.es 3008

# Usar curl para probar
curl -u hazrakh:PASSWORD ftp://reinosdeleyenda.es:3008/ --connect-timeout 10

# Usar Python para conectar
python3 -c "from ftplib import FTP; ftp = FTP(); ftp.connect('reinosdeleyenda.es', 3008); ftp.login('hazrakh', 'PASSWORD')"
```

## Referencias

- Documentación del MUD: https://reinosdeleyenda.es
- Contacto administrador: @mordisko (Telegram)
- Última credencial compartida: 24/01/2024 por Mordisco
"""

# mudctl — Documentación de Investigación

## Protocolo del puerto 3008

### Contexto
El servidor FTP de Reinos de Leyenda usa el puerto 3008, que no es el puerto FTP estándar (21), ni el puerto SFTP estándar (22). Se necesita determinar qué protocolo responde en ese puerto para implementar el backend correcto en mudctl.

### Opciones a verificar
1. **FTP estándar (ftplib)**: Conectar al puerto 3008 y ver si responde al banner de FTP.
2. **FTPS con TLS**: Si el servidor soporta FTPS explícito sobre el puerto 3008.
3. **SFTP sobre SSH**: Si el puerto 3008 es realmente un servidor SSH/SFTP.

### Comandos de verificación (probar con el servidor)
- `curl -v telnet://reinosdeleyenda.es:3008` — ver el banner inicial
- `python -c "import ftplib; f=ftplib.FTP(); f.connect('reinosdeleyenda.es', 3008); print(f.getwelcome())"` — probar FTP
- `python -c "import paramiko; s=paramiko.SSHClient(); s.connect('reinosdeleyenda.es', 3008, 'hazrakh'); print('SFTP OK')"` — probar SFTP

### Notas
- Mordisko dio las credenciales el 24/01/2024 y advirtió el 20/09/2025 que da/quita accesos seguido.
- La credencial última conocida es para el usuario 'hazrakh' en host 'reinosdeleyenda.es', puerto 3008.
- Confirmar vigencia de credenciales antes de usar.

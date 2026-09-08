# LPC en Reinos de Leyenda — apuntes

## Verificado
- RdL es un MUD LPC. Corre un driver MudOS con mudlib propia llamada pusa, muy modificada desde 1996.
- LPC está basado en C y orientado a objetos. Todo el contenido del juego se programa en LPC.
- Cada fichero con extensión .c es un objeto: habitaciones, armas, monstruos, jugadores, bolsas.
- Los ficheros .h son cabeceras: se usan con inherit e includes para reutilizar la mudlib base.
- La forma típica de crear algo propio es heredar de un objeto base de la mudlib y especializarlo.
- Ejemplo mínimo visto en el falso local (ilustrativo, no del servidor real):
  hereda de arma
  objeto espada

## Pendiente de confirmar
- Miguel recuerda una o dos extensiones más además de .c y .h pero no cuáles. Candidatos habituales en MUDs: ficheros de guardado, logs y documentación. No se asume ninguno.
- Cómo confirmar: en cuanto haya acceso real, listar la raíz y las carpetas de otros inmos y anotar las extensiones que aparezcan. La constante LPC_EXTS de mudctl se amplía entonces.
- Sintaxis exacta de inherit, includes y funciones de la mudlib pusa. Se irá copiando de ejemplos reales a docs/recetas.md.
- Ruta exacta de tu carpeta personal en el servidor. Se asume barra más tu usuario por MUD_HOME hasta ver el listado real.

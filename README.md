# library-management-system
Sistema de gestión de una biblioteca.

Entidades
- Usuario
- Libro
- Autor
- Préstamo
- Reserva
- Multa

Reglas de negocio
- Un usuario puede tener como máximo 5 préstamos activos.
- No se puede prestar un libro ya prestado.
- Una reserva solo puede hacerse si el libro no está disponible.
- Una devolución fuera de plazo genera una multa.
- Si existe una reserva, el siguiente préstamo debe ser para el primer usuario de la cola.
- Los usuarios con multas pendientes no pueden pedir nuevos libros.
- Un libro puede quedar marcado como perdido.
- Si un libro está perdido no puede prestarse.
- Los administradores pueden eliminar libros solo si no tienen préstamos activos.
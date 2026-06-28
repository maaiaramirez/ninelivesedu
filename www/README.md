# Nine Lives Edu - Plataforma de Tutorías Online

Una plataforma web moderna y completa para conectar estudiantes con tutores y recursos educativos.

## 🚀 Características Principales

### Página Principal
- **Header fijo** con logo y navegación limpia
- **Sección Hero** impactante con llamadas a la acción
- **Beneficios destacados** con iconos y descripciones
- **Testimonios** de estudiantes y tutores
- **Llamada a la acción** con diseño atractivo
- **Footer completo** con enlaces y redes sociales

### Biblioteca de Apuntes
- **Buscador avanzado** con filtros por nivel, materia y palabras clave
- **Panel de filtros laterales** con opciones adicionales
- **Vista de tarjetas y lista** intercambiable
- **Sistema de subida** de nuevos apuntes
- **Calificaciones y reseñas** de usuarios
- **Paginación** para navegación eficiente

### Catálogo de Tutores
- **Perfiles detallados** con fotos, biografías y especialidades
- **Sistema de filtros** por nivel, materia, precio y valoración
- **Calendario de disponibilidad** integrado
- **Sistema de reservas** con botones de acción rápida
- **Reseñas y calificaciones** de estudiantes
- **Modal de perfil completo** con toda la información

### Foros Comunitarios
- **Categorización por nivel y materia**
- **Diferentes tipos de posts**: preguntas, debates, recursos, anuncios
- **Sistema de votación** y respuestas
- **Búsqueda avanzada** en contenido y etiquetas
- **Moderación** y organización automática
- **Interfaz intuitiva** para participación activa

## 🎨 Diseño y UX

### Paleta de Colores
Basada en el logo proporcionado:
- **Púrpura/Magenta**: `#8b5cf6` a `#ec4899` (gradientes principales)
- **Naranja**: `#ff6b35` a `#f97316` (botones destacados)
- **Azul**: `#667eea` a `#764ba2` (fondos hero y CTA)
- **Grises**: `#333`, `#666`, `#f8f9fa` (textos y fondos)

### Tipografía
- **Fuente principal**: Poppins (Google Fonts)
- **Pesos**: 300, 400, 500, 600, 700
- **Jerarquía clara** con tamaños escalables

### Elementos de Diseño
- **Bordes redondeados** en todos los elementos
- **Sombras suaves** para profundidad
- **Gradientes** para elementos destacados
- **Iconos Font Awesome** para mejor UX
- **Animaciones sutiles** en hover y transiciones

## 📱 Responsividad

### Breakpoints
- **Desktop**: 1200px+
- **Tablet**: 768px - 1199px
- **Mobile**: 320px - 767px

### Adaptaciones Móviles
- **Header colapsable** en móviles
- **Grids responsivos** que se adaptan al tamaño
- **Botones táctiles** optimizados
- **Navegación simplificada**
- **Contenido apilable** verticalmente

## 🛠️ Tecnologías Utilizadas

### Frontend
- **HTML5** semántico y accesible
- **CSS3** con Grid y Flexbox
- **JavaScript ES6+** vanilla
- **Font Awesome** para iconos
- **Google Fonts** para tipografía

### Características Técnicas
- **Diseño mobile-first**
- **CSS Grid y Flexbox** para layouts
- **Variables CSS** para consistencia
- **Animaciones CSS** suaves
- **JavaScript modular** y organizado

## 📁 Estructura del Proyecto

```
nine-lives-edu/
├── index.html          # Página principal
├── apuntes.html        # Biblioteca de apuntes
├── tutores.html        # Catálogo de tutores
├── foros.html          # Foros comunitarios
├── styles.css          # Estilos principales
├── apuntes.css         # Estilos específicos apuntes
├── tutores.css         # Estilos específicos tutores
├── foros.css           # Estilos específicos foros
├── script.js           # JavaScript principal
├── apuntes.js          # JavaScript apuntes
├── tutores.js          # JavaScript tutores
├── foros.js            # JavaScript foros
└── README.md           # Documentación
```

## 🚀 Instalación y Uso

### Requisitos
- Navegador web moderno
- Servidor web local (opcional)

### Instalación
1. Clona o descarga el proyecto
2. Abre `index.html` en tu navegador
3. O usa un servidor local para mejor experiencia

### Servidor Local (Recomendado)
```bash
# Con Python
python -m http.server 8000

# Con Node.js
npx serve .

# Con PHP
php -S localhost:8000
```

## 🎯 Funcionalidades Implementadas

### ✅ Completadas
- [x] Página principal con hero y secciones
- [x] Sistema de navegación fijo
- [x] Biblioteca de apuntes con filtros
- [x] Catálogo de tutores con perfiles
- [x] Foros comunitarios con categorías
- [x] Diseño responsivo completo
- [x] Modales interactivos
- [x] Sistema de búsqueda avanzada
- [x] Animaciones y transiciones

### 🔄 Pendientes (Futuras Implementaciones)
- [ ] Sistema de reservas con calendario real
- [ ] Integración de pagos (Stripe/PayPal)
- [ ] Sistema de videollamadas (WebRTC)
- [ ] Panel de usuario personalizado
- [ ] Sistema de notificaciones
- [ ] Base de datos backend
- [ ] Autenticación de usuarios
- [ ] Sistema de moderación avanzado

## 🎨 Personalización

### Colores
Los colores se pueden modificar fácilmente en las variables CSS:
```css
:root {
    --primary-purple: #8b5cf6;
    --primary-pink: #ec4899;
    --accent-orange: #ff6b35;
    --accent-orange-dark: #f97316;
}
```

### Logo
Reemplaza `logo.png` con tu propio logo manteniendo las dimensiones recomendadas.

## 📞 Soporte

Para soporte técnico o consultas sobre el proyecto:
- **Email**: contacto@ninelivesedu.com
- **Documentación**: Ver comentarios en el código

## 📄 Licencia

Este proyecto está desarrollado para fines educativos y de demostración.

---

**Nine Lives Edu** - Aprende sin límites 🎓

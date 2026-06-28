const posts = [
  {
    id: 'post-1',
    titulo: '¿Cómo resolver ecuaciones cuadráticas por factorización?',
    contenido: 'Estoy teniendo problemas para entender cómo factorizar ecuaciones cuadráticas. ¿Alguien puede explicarme el proceso paso a paso con ejemplos?',
    autor: 'Carlos M.',
    fecha: '2024-01-15',
    nivel: 'secundaria',
    materia: 'matematicas',
    tipo: 'pregunta',
    tags: ['ecuaciones', 'factorización', 'álgebra'],
    votos: 12,
    respuestas: 2,
    vistas: 156,
    resuelto: false,
    responses: [
      {
        id: 'resp-1',
        autor: 'Prof. María G.',
        fecha: '2024-01-15',
        texto: 'Para factorizar, primero identifica dos números que multiplicados den el término independiente y sumados el coeficiente del término lineal.'
      },
      {
        id: 'resp-2',
        autor: 'Ana S.',
        fecha: '2024-01-15',
        texto: 'Recuerda verificar la respuesta sustituyendo en la ecuación original.'
      }
    ]
  },
  {
    id: 'post-2',
    titulo: 'Debate: ¿Es mejor estudiar en grupo o individualmente?',
    contenido: 'Quiero conocer sus opiniones sobre los pros y contras de estudiar en grupo versus estudiar solo. ¿Cuál método prefieren y por qué?',
    autor: 'Ana L.',
    fecha: '2024-01-14',
    nivel: 'universidad',
    materia: 'general',
    tipo: 'debate',
    tags: ['estudio', 'métodos', 'productividad'],
    votos: 25,
    respuestas: 3,
    vistas: 234,
    resuelto: false,
    responses: [
      {
        id: 'resp-3',
        autor: 'Luis P.',
        fecha: '2024-01-14',
        texto: 'Depende del tema. Para materias teóricas prefiero estudiar solo, pero para ejercicios me sirve el grupo.'
      },
      {
        id: 'resp-4',
        autor: 'María T.',
        fecha: '2024-01-14',
        texto: 'El grupo ayuda a mantener la motivación, aunque es más difícil coordinar horarios.'
      },
      {
        id: 'resp-5',
        autor: 'Jorge R.',
        fecha: '2024-01-14',
        texto: 'Combinando ambos métodos obtengo mejores resultados.'
      }
    ]
  },
  {
    id: 'post-3',
    titulo: 'Recursos útiles para aprender Física Cuántica',
    contenido: 'Comparto una lista de recursos que me han ayudado mucho en mi curso de física cuántica: libros, videos, simulaciones y ejercicios prácticos.',
    autor: 'Prof. Miguel T.',
    fecha: '2024-01-13',
    nivel: 'universidad',
    materia: 'fisica',
    tipo: 'recurso',
    tags: ['física cuántica', 'recursos', 'libros'],
    votos: 18,
    respuestas: 1,
    vistas: 189,
    resuelto: false,
    responses: [
      {
        id: 'resp-6',
        autor: 'Laura Z.',
        fecha: '2024-01-13',
        texto: '¡Gracias! Agregaría el canal de Quantum Crash Course en YouTube.'
      }
    ]
  },
  {
    id: 'post-4',
    titulo: 'Anuncio: Nuevo grupo de estudio de Química Orgánica',
    contenido: 'Estoy formando un grupo de estudio para química orgánica. Nos reuniremos los martes y jueves a las 7 PM. ¡Interesados contáctenme!',
    autor: 'Dra. Patricia V.',
    fecha: '2024-01-12',
    nivel: 'universidad',
    materia: 'quimica',
    tipo: 'anuncio',
    tags: ['grupo de estudio', 'química orgánica', 'reuniones'],
    votos: 7,
    respuestas: 0,
    vistas: 98,
    resuelto: false,
    responses: []
  },
  {
    id: 'post-5',
    titulo: '¿Cuál es la diferencia entre mitosis y meiosis?',
    contenido: 'Necesito ayuda para entender las diferencias principales entre mitosis y meiosis. ¿Pueden explicarme cada proceso y sus diferencias?',
    autor: 'Laura S.',
    fecha: '2024-01-11',
    nivel: 'bachillerato',
    materia: 'biologia',
    tipo: 'pregunta',
    tags: ['mitosis', 'meiosis', 'división celular'],
    votos: 9,
    respuestas: 2,
    vistas: 127,
    resuelto: true,
    responses: [
      {
        id: 'resp-7',
        autor: 'Dra. Patricia V.',
        fecha: '2024-01-11',
        texto: 'La mitosis genera dos células hijas idénticas, mientras que la meiosis produce cuatro células con la mitad del material genético.'
      },
      {
        id: 'resp-8',
        autor: 'Diego R.',
        fecha: '2024-01-11',
        texto: 'En meiosis existen dos divisiones consecutivas y ocurre recombinación genética.'
      }
    ]
  },
  {
    id: 'post-6',
    titulo: 'Técnicas de memorización para Historia',
    contenido: 'Comparto algunas técnicas que uso para memorizar fechas y eventos históricos. Espero que les sean útiles para sus exámenes.',
    autor: 'Diego R.',
    fecha: '2024-01-10',
    nivel: 'secundaria',
    materia: 'historia',
    tipo: 'recurso',
    tags: ['memorización', 'historia', 'técnicas'],
    votos: 14,
    respuestas: 1,
    vistas: 145,
    resuelto: false,
    responses: [
      {
        id: 'resp-9',
        autor: 'Sofia C.',
        fecha: '2024-01-10',
        texto: 'El uso de líneas de tiempo visuales también ayuda muchísimo.'
      }
    ]
  },
  {
    id: 'post-7',
    titulo: '¿Cómo mejorar mi comprensión lectora en Literatura?',
    contenido: 'Tengo dificultades para entender textos literarios complejos. ¿Qué estrategias puedo usar para mejorar mi comprensión lectora?',
    autor: 'Sofia C.',
    fecha: '2024-01-09',
    nivel: 'bachillerato',
    materia: 'literatura',
    tipo: 'pregunta',
    tags: ['comprensión lectora', 'literatura', 'estrategias'],
    votos: 11,
    respuestas: 2,
    vistas: 167,
    resuelto: false,
    responses: [
      {
        id: 'resp-10',
        autor: 'Dra. Carmen L.',
        fecha: '2024-01-09',
        texto: 'Lee dos veces el texto, la primera para entender la trama y la segunda para analizar recursos literarios.'
      },
      {
        id: 'resp-11',
        autor: 'Marcos Q.',
        fecha: '2024-01-09',
        texto: 'Subraya conceptos clave y escribe resúmenes cortos por capítulo.'
      }
    ]
  },
  {
    id: 'post-8',
    titulo: 'Debate: ¿Debería ser obligatorio el inglés en la universidad?',
    contenido: '¿Qué opinan sobre hacer obligatorio el inglés en todas las carreras universitarias? ¿Creen que es necesario o debería ser opcional?',
    autor: 'Roberto V.',
    fecha: '2024-01-08',
    nivel: 'universidad',
    materia: 'ingles',
    tipo: 'debate',
    tags: ['inglés', 'universidad', 'obligatorio'],
    votos: 22,
    respuestas: 2,
    vistas: 298,
    resuelto: false,
    responses: [
      {
        id: 'resp-12',
        autor: 'John S.',
        fecha: '2024-01-08',
        texto: 'El inglés abre puertas profesionales, debería haber al menos un nivel básico obligatorio.'
      },
      {
        id: 'resp-13',
        autor: 'Lucía P.',
        fecha: '2024-01-08',
        texto: 'Podría ser opcional pero con incentivos para quienes lo completen.'
      }
    ]
  }
];

module.exports = { posts };


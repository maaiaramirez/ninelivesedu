const tutores = [
  {
    id: 'tutor-1',
    nombre: 'Dr. María González',
    materia: 'matematicas',
    nivel: 'universidad',
    precio: 35,
    rating: 4.9,
    experiencia: '8 años',
    foto: 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face',
    biografia: 'Doctora en Matemáticas con más de 8 años de experiencia enseñando cálculo, álgebra y estadística. Especializada en preparación para exámenes universitarios.',
    materias: ['Cálculo', 'Álgebra', 'Estadística', 'Geometría'],
    disponibilidad: {
      lunes: 'mañana',
      martes: 'tarde',
      miercoles: 'mañana',
      jueves: 'tarde',
      viernes: 'mañana',
      sabado: 'disponible',
      domingo: 'no disponible'
    },
    idiomas: ['español', 'ingles'],
    reseñas: [
      { autor: 'Carlos M.', rating: 5, texto: 'Excelente profesora, muy clara en sus explicaciones.' },
      { autor: 'Ana L.', rating: 5, texto: 'Me ayudó mucho con cálculo diferencial.' },
      { autor: 'Pedro R.', rating: 4, texto: 'Muy paciente y dedicada.' }
    ]
  },
  {
    id: 'tutor-2',
    nombre: 'Prof. Carlos Ruiz',
    materia: 'fisica',
    nivel: 'bachillerato',
    precio: 25,
    rating: 4.7,
    experiencia: '5 años',
    foto: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face',
    biografia: 'Ingeniero Físico con amplia experiencia en enseñanza de física a nivel bachillerato. Especializado en mecánica y termodinámica.',
    materias: ['Física', 'Mecánica', 'Termodinámica', 'Óptica'],
    disponibilidad: {
      lunes: 'tarde',
      martes: 'mañana',
      miercoles: 'tarde',
      jueves: 'mañana',
      viernes: 'tarde',
      sabado: 'disponible',
      domingo: 'disponible'
    },
    idiomas: ['español'],
    reseñas: [
      { autor: 'Laura S.', rating: 5, texto: 'Muy bueno explicando conceptos difíciles.' },
      { autor: 'Miguel T.', rating: 4, texto: 'Clases muy dinámicas y entretenidas.' }
    ]
  },
  {
    id: 'tutor-3',
    nombre: 'Dra. Ana Martínez',
    materia: 'quimica',
    nivel: 'universidad',
    precio: 30,
    rating: 4.8,
    experiencia: '6 años',
    foto: 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face',
    biografia: 'Doctora en Química Orgánica con experiencia en investigación y docencia universitaria. Especializada en química orgánica y bioquímica.',
    materias: ['Química Orgánica', 'Bioquímica', 'Química Inorgánica', 'Fisicoquímica'],
    disponibilidad: {
      lunes: 'mañana',
      martes: 'no disponible',
      miercoles: 'mañana',
      jueves: 'tarde',
      viernes: 'mañana',
      sabado: 'no disponible',
      domingo: 'no disponible'
    },
    idiomas: ['español', 'ingles'],
    reseñas: [
      { autor: 'Roberto V.', rating: 5, texto: 'Increíble profesora, muy detallada.' },
      { autor: 'Sofia C.', rating: 5, texto: 'Me salvó en química orgánica.' }
    ]
  },
  {
    id: 'tutor-4',
    nombre: 'Prof. Luis García',
    materia: 'historia',
    nivel: 'secundaria',
    precio: 20,
    rating: 4.6,
    experiencia: '4 años',
    foto: 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face',
    biografia: 'Licenciado en Historia con especialización en historia universal y arte. Experiencia enseñando a estudiantes de secundaria.',
    materias: ['Historia Universal', 'Historia del Arte', 'Geografía', 'Ciencias Sociales'],
    disponibilidad: {
      lunes: 'tarde',
      martes: 'tarde',
      miercoles: 'tarde',
      jueves: 'tarde',
      viernes: 'tarde',
      sabado: 'disponible',
      domingo: 'disponible'
    },
    idiomas: ['español'],
    reseñas: [
      { autor: 'Elena P.', rating: 4, texto: 'Muy interesante, hace la historia divertida.' },
      { autor: 'Diego M.', rating: 5, texto: 'Excelente profesor, muy preparado.' }
    ]
  },
  {
    id: 'tutor-5',
    nombre: 'Dra. Carmen López',
    materia: 'literatura',
    nivel: 'bachillerato',
    precio: 28,
    rating: 4.9,
    experiencia: '7 años',
    foto: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&h=150&fit=crop&crop=face',
    biografia: 'Doctora en Literatura Española con amplia experiencia en análisis literario y redacción. Especializada en literatura clásica y contemporánea.',
    materias: ['Literatura Española', 'Redacción', 'Análisis Literario', 'Lingüística'],
    disponibilidad: {
      lunes: 'mañana',
      martes: 'mañana',
      miercoles: 'no disponible',
      jueves: 'mañana',
      viernes: 'mañana',
      sabado: 'disponible',
      domingo: 'no disponible'
    },
    idiomas: ['español', 'frances'],
    reseñas: [
      { autor: 'Isabel R.', rating: 5, texto: 'Mejor profesora de literatura que he tenido.' },
      { autor: 'Antonio G.', rating: 5, texto: 'Muy buena para análisis de textos.' }
    ]
  },
  {
    id: 'tutor-6',
    nombre: 'Prof. John Smith',
    materia: 'ingles',
    nivel: 'universidad',
    precio: 40,
    rating: 4.8,
    experiencia: '10 años',
    foto: 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face',
    biografia: 'Nativo inglés con certificación TESOL y más de 10 años de experiencia enseñando inglés como segunda lengua. Especializado en preparación para exámenes internacionales.',
    materias: ['Inglés Conversacional', 'TOEFL', 'IELTS', 'Business English'],
    disponibilidad: {
      lunes: 'disponible',
      martes: 'disponible',
      miercoles: 'disponible',
      jueves: 'disponible',
      viernes: 'disponible',
      sabado: 'disponible',
      domingo: 'disponible'
    },
    idiomas: ['ingles', 'español'],
    reseñas: [
      { autor: 'María F.', rating: 5, texto: 'Nativo perfecto, muy profesional.' },
      { autor: 'Carlos D.', rating: 4, texto: 'Excelente para preparar TOEFL.' }
    ]
  },
  {
    id: 'tutor-7',
    nombre: 'Dra. Patricia Vega',
    materia: 'biologia',
    nivel: 'universidad',
    precio: 32,
    rating: 4.7,
    experiencia: '6 años',
    foto: 'https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=150&h=150&fit=crop&crop=face',
    biografia: 'Doctora en Biología Molecular con experiencia en investigación y docencia. Especializada en biología celular y genética.',
    materias: ['Biología Celular', 'Genética', 'Microbiología', 'Ecología'],
    disponibilidad: {
      lunes: 'tarde',
      martes: 'mañana',
      miercoles: 'tarde',
      jueves: 'mañana',
      viernes: 'tarde',
      sabado: 'no disponible',
      domingo: 'no disponible'
    },
    idiomas: ['español', 'ingles'],
    reseñas: [
      { autor: 'Alejandro H.', rating: 5, texto: 'Muy clara en sus explicaciones de biología.' },
      { autor: 'Valeria M.', rating: 4, texto: 'Excelente para genética.' }
    ]
  },
  {
    id: 'tutor-8',
    nombre: 'Prof. Miguel Torres',
    materia: 'filosofia',
    nivel: 'bachillerato',
    precio: 22,
    rating: 4.5,
    experiencia: '3 años',
    foto: 'https://images.unsplash.com/photo-1560250097-0b93528c311a?w=150&h=150&fit=crop&crop=face',
    biografia: 'Licenciado en Filosofía con especialización en filosofía moderna y ética. Experiencia enseñando a estudiantes de bachillerato.',
    materias: ['Filosofía Moderna', 'Ética', 'Lógica', 'Historia de la Filosofía'],
    disponibilidad: {
      lunes: 'noche',
      martes: 'noche',
      miercoles: 'noche',
      jueves: 'noche',
      viernes: 'noche',
      sabado: 'disponible',
      domingo: 'disponible'
    },
    idiomas: ['español'],
    reseñas: [
      { autor: 'Gabriel L.', rating: 4, texto: 'Muy bueno para entender conceptos filosóficos.' },
      { autor: 'Natalia K.', rating: 5, texto: 'Hace la filosofía muy interesante.' }
    ]
  }
];

const swapRequests = [];

module.exports = { tutores, swapRequests };


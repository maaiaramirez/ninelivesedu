import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import axios from 'axios';

// La misma IP que configuramos en el Login
const API_URL = 'https://some-suns-deny.loca.lt';
export default function DashboardScreen() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  useEffect(() => {
    // Ejemplo: consultar un endpoint de estado al cargar el dashboard
    axios.get(`${API_URL}/status`)
      .then(response => {
        setData(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error(error);
        Alert.alert('Error', 'No se pudo conectar con el servidor de datos');
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>¡Bienvenido al Dashboard!</Text>
      <Text>Estado del sistema: {data ? 'Conectado' : 'Desconectado'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({ 
  container: { flex: 1, alignItems: 'center', justifyContent: 'center' }, 
  title: { fontSize: 20, marginBottom: 20 } 
});
import { useState, useEffect } from 'react';

function getWeatherIcon(desc = '') {
  const d = desc.toLowerCase();
  if (d.includes('sunny') || d.includes('clear')) return '☀️';
  if (d.includes('cloud')) return '☁️';
  if (d.includes('rain')) return '🌧️';
  if (d.includes('thunder') || d.includes('storm')) return '⛈️';
  if (d.includes('snow')) return '❄️';
  if (d.includes('fog') || d.includes('mist')) return '🌫️';
  if (d.includes('overcast')) return '🌥️';
  return '🌡️';
}

export function useClock() {
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');
  const [weather, setWeather] = useState({ icon: '🌡️', temp: '--', city: 'Loading...' });

  // Clock tick
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const hh = String(now.getHours()).padStart(2, '0');
      const mm = String(now.getMinutes()).padStart(2, '0');
      const ss = String(now.getSeconds()).padStart(2, '0');
      setTime(`${hh}:${mm}:${ss}`);
      setDate(now.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Weather fetch
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const res = await fetch('/api/weather');
        if (!res.ok) throw new Error();
        const data = await res.json();
        const c = data.current_condition?.[0];
        const area = data.nearest_area?.[0]?.areaName?.[0]?.value ?? 'Unknown';
        setWeather({
          icon: getWeatherIcon(c?.weatherDesc?.[0]?.value ?? ''),
          temp: `${c?.temp_C ?? '--'}°C`,
          city: area,
        });
      } catch {
        setWeather({ icon: '📡', temp: '--', city: 'Offline' });
      }
    };
    fetchWeather();
    const id = setInterval(fetchWeather, 30 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  return { time, date, weather };
}

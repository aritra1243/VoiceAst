import { useState, useRef, useCallback } from 'react';

export function useSpeech({ onTranscript, onFinal }) {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  const setup = useCallback(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    const r = new SR();
    r.continuous = false;
    r.interimResults = true;
    r.lang = 'en-US';

    r.onstart = () => setIsListening(true);

    r.onresult = (e) => {
      let final = '';
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript;
        else interim += e.results[i][0].transcript;
      }
      if (onTranscript) onTranscript(final || interim);
      if (final && onFinal) onFinal(final.trim());
    };

    r.onend = () => setIsListening(false);
    r.onerror = () => setIsListening(false);

    return r;
  }, [onTranscript, onFinal]);

  const startListening = useCallback(() => {
    if (isListening) return;
    if (!recognitionRef.current) recognitionRef.current = setup();
    if (!recognitionRef.current) return;
    try { recognitionRef.current.start(); } catch (_) {}
  }, [isListening, setup]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
    }
    setIsListening(false);
  }, []);

  return { isListening, startListening, stopListening };
}

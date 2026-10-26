import {
  forwardRef, useCallback, useImperativeHandle, useRef, useState,
} from 'react';

/**
 * Canvas de firma reutilizable.
 * Expone getDataURL(), isEmpty() y clear() mediante ref.
 */
const SignaturePad = forwardRef(function SignaturePad({ label, hint }, ref) {
  const canvasRef = useRef(null);
  const dibujando = useRef(false);
  const ultimo = useRef({ x: 0, y: 0 });
  const [vacio, setVacio] = useState(true);

  const limpiar = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    setVacio(true);
  }, []);

  useImperativeHandle(ref, () => ({
    getDataURL: () => {
      const canvas = canvasRef.current;
      if (!canvas || vacio) return '';
      return canvas.toDataURL('image/png');
    },
    isEmpty: () => vacio,
    clear: limpiar,
  }), [limpiar, vacio]);

  const posicion = (evento) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((evento.clientX - rect.left) / rect.width) * canvas.width,
      y: ((evento.clientY - rect.top) / rect.height) * canvas.height,
    };
  };

  const iniciar = (evento) => {
    evento.preventDefault();
    dibujando.current = true;
    ultimo.current = posicion(evento);
  };

  const mover = (evento) => {
    if (!dibujando.current) return;
    evento.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const punto = posicion(evento);
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(ultimo.current.x, ultimo.current.y);
    ctx.lineTo(punto.x, punto.y);
    ctx.stroke();
    ultimo.current = punto;
    if (vacio) setVacio(false);
  };

  const terminar = () => { dibujando.current = false; };

  return (
    <div className="sig-box">
      <div className="sig-label">
        <span>{label}</span>
        <button type="button" className="link" onClick={limpiar}>Limpiar</button>
      </div>
      <canvas
        ref={canvasRef}
        className="sig-canvas"
        width={600}
        height={150}
        aria-label={label}
        onPointerDown={iniciar}
        onPointerMove={mover}
        onPointerUp={terminar}
        onPointerLeave={terminar}
      />
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
});

export default SignaturePad;

// static/js/order-socket.js

function setupOrderWebSocket(orderId, onUpdate) {
    const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/order/${orderId}/`);
  
    socket.onopen = () => console.log("📡 WebSocket connected for order:", orderId);
  
    socket.onerror = (err) => console.error("❌ WebSocket error", err);
  
    socket.onclose = (e) => console.warn("🔌 WebSocket closed", e);
  
    socket.onmessage = function (e) {
      try {
        const data = JSON.parse(e.data);
        if (data.event) {
          console.log(`📩 WS Event: ${data.event}`, data);
          onUpdate(data.event, data);
        }
      } catch (err) {
        console.warn("Invalid WS message", e.data);
      }
    };
  
    return socket;
  }
  
// order-socket.js
window.setupOrderWebSocket = function(orderId, callback) {
  const socket = new WebSocket(`ws://${window.location.host}/ws/order/${orderId}/`);
  
  socket.onopen = () => {
      console.log(`WebSocket connected for order ${orderId}`);
  };
  
  socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message:', data);
      callback(data.event, data);
  };
  
  socket.onclose = () => {
      console.log('WebSocket closed, attempting to reconnect...');
      setTimeout(() => setupOrderWebSocket(orderId, callback), 1000);
  };
  
  socket.onerror = (error) => {
      console.error('WebSocket error:', error);
  };
};
/**
 * Production-ready WebSocket service with reconnection and error handling
 */

export enum WSReadyState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

export interface WSMessage {
  type: string;
  payload: any;
  timestamp?: number;
}

export interface WSConfig {
  url: string;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  messageQueueSize?: number;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: Required<WSConfig>;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private messageQueue: WSMessage[] = [];
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private isIntentionallyClosed = false;

  constructor(config: WSConfig) {
    this.config = {
      reconnect: true,
      reconnectInterval: 5000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
      messageQueueSize: 100,
      ...config,
    };
  }

  /**
   * Connect to WebSocket server
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WSReadyState.OPEN) {
        resolve();
        return;
      }

      try {
        this.isIntentionallyClosed = false;
        this.ws = new WebSocket(this.config.url);

        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          this.flushMessageQueue();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.stopHeartbeat();
          
          if (!this.isIntentionallyClosed && this.config.reconnect) {
            this.attemptReconnect();
          }
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isIntentionallyClosed = true;
    this.stopHeartbeat();
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
  }

  /**
   * Send message through WebSocket
   */
  send(type: string, payload: any): void {
    const message: WSMessage = {
      type,
      payload,
      timestamp: Date.now(),
    };

    if (this.ws && this.ws.readyState === WSReadyState.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Queue message if not connected
      this.queueMessage(message);
    }
  }

  /**
   * Subscribe to specific message type
   */
  on(type: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    
    this.listeners.get(type)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.listeners.get(type);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.listeners.delete(type);
        }
      }
    };
  }

  /**
   * Get current connection state
   */
  getState(): WSReadyState {
    return this.ws ? this.ws.readyState : WSReadyState.CLOSED;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WSReadyState.OPEN;
  }

  private handleMessage(message: WSMessage): void {
    // Handle heartbeat response
    if (message.type === 'pong') {
      return;
    }

    // Notify listeners
    const callbacks = this.listeners.get(message.type);
    if (callbacks) {
      callbacks.forEach(callback => {
        try {
          callback(message.payload);
        } catch (error) {
          console.error(`Error in WebSocket listener for ${message.type}:`, error);
        }
      });
    }

    // Also notify wildcard listeners
    const wildcardCallbacks = this.listeners.get('*');
    if (wildcardCallbacks) {
      wildcardCallbacks.forEach(callback => {
        try {
          callback(message);
        } catch (error) {
          console.error('Error in WebSocket wildcard listener:', error);
        }
      });
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.config.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
    
    console.log(`Attempting reconnection ${this.reconnectAttempts}/${this.config.maxReconnectAttempts} in ${delay}ms`);

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send('ping', { timestamp: Date.now() });
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private queueMessage(message: WSMessage): void {
    this.messageQueue.push(message);
    
    // Limit queue size
    if (this.messageQueue.length > this.config.messageQueueSize) {
      this.messageQueue.shift();
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift();
      if (message && this.ws) {
        this.ws.send(JSON.stringify(message));
      }
    }
  }
}

// Singleton instance for app-wide WebSocket connection
let wsInstance: WebSocketService | null = null;

export function getWebSocketService(): WebSocketService {
  if (!wsInstance) {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 
                  (process.env.NEXT_PUBLIC_API_BASE?.replace(/^http/, 'ws') + '/ws') ||
                  'ws://localhost:8000/ws';
    
    wsInstance = new WebSocketService({
      url: wsUrl,
      reconnect: true,
      reconnectInterval: 3000,
      maxReconnectAttempts: 10,
      heartbeatInterval: 30000,
    });
  }
  
  return wsInstance;
}

// Helper function for job-specific WebSocket connections
export function connectJobWebSocket(
  jobId: string,
  onUpdate: (update: any) => void,
  onError?: (error: any) => void
): () => void {
  const wsService = getWebSocketService();
  
  // Connect if not already connected
  if (!wsService.isConnected()) {
    wsService.connect().catch(error => {
      console.error('Failed to connect WebSocket:', error);
      onError?.(error);
    });
  }

  // Subscribe to job updates
  const unsubscribe = wsService.on(`job:${jobId}`, onUpdate);
  
  // Subscribe to job errors
  const unsubscribeError = wsService.on(`job:${jobId}:error`, (error) => {
    onError?.(error);
  });

  // Send subscription message
  wsService.send('subscribe', { jobId });

  // Return cleanup function
  return () => {
    unsubscribe();
    unsubscribeError();
    wsService.send('unsubscribe', { jobId });
  };
}
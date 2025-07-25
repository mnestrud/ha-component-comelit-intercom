import { IconaBridgeClient, ICONA_BRIDGE_PORT } from 'comelit-client';
import net from 'net';
import fs from 'fs';
import path from 'path';

// Configuration from environment
const COMELIT_IP = process.env.COMELIT_IP_ADDRESS || '10.0.1.49';
const COMELIT_TOKEN = process.env.COMELIT_TOKEN || '9943a85362467c53586e3553d34f8a8d';

// Create output directory
const outputDir = path.join(process.cwd(), 'protocol-captures');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Logger that captures all operations
class ProtocolLogger {
  constructor(sessionName) {
    this.sessionName = sessionName;
    this.logFile = path.join(outputDir, `${sessionName}.json`);
    this.operations = [];
    this.startTime = Date.now();
  }

  log(level, message, data = {}) {
    const entry = {
      timestamp: Date.now() - this.startTime,
      level,
      message,
      ...data
    };
    this.operations.push(entry);
    console.log(`[${level}] ${message}`, data);
  }

  info(message, data) { this.log('info', message, data); }
  debug(message, data) { this.log('debug', message, data); }
  warn(message, data) { this.log('warn', message, data); }
  error(message, data) { this.log('error', message, data); }

  save() {
    fs.writeFileSync(this.logFile, JSON.stringify(this.operations, null, 2));
    console.log(`\nProtocol capture saved to: ${this.logFile}`);
  }
}

// Proxy socket to capture raw bytes
class SocketProxy {
  constructor(realSocket, logger) {
    this.socket = realSocket;
    this.logger = logger;
    this.operationId = 0;
  }

  async connect(port, host) {
    this.logger.info('CONNECT', { port, host });
    return new Promise((resolve, reject) => {
      this.socket.connect(port, host, () => {
        this.logger.info('CONNECTED', { port, host });
        resolve();
      });
      this.socket.on('error', reject);
    });
  }

  async writeAll(buffer) {
    this.operationId++;
    const hexDump = buffer.toString('hex').match(/.{1,2}/g).join(' ');
    this.logger.info('WRITE', {
      operationId: this.operationId,
      bytes: hexDump,
      length: buffer.length,
      ascii: buffer.toString('ascii').replace(/[\x00-\x1F\x7F-\xFF]/g, '.')
    });
    return new Promise((resolve, reject) => {
      this.socket.write(buffer, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });
  }

  async read(size) {
    return new Promise((resolve, reject) => {
      const chunks = [];
      let totalRead = 0;

      const onData = (chunk) => {
        chunks.push(chunk);
        totalRead += chunk.length;
        
        if (totalRead >= size) {
          this.socket.removeListener('data', onData);
          const buffer = Buffer.concat(chunks).slice(0, size);
          const hexDump = buffer.toString('hex').match(/.{1,2}/g).join(' ');
          
          this.logger.info('READ', {
            operationId: this.operationId,
            bytes: hexDump,
            length: buffer.length,
            ascii: buffer.toString('ascii').replace(/[\x00-\x1F\x7F-\xFF]/g, '.')
          });
          
          resolve(buffer);
        }
      };

      this.socket.on('data', onData);
      this.socket.on('error', reject);
    });
  }

  async end() {
    this.logger.info('CLOSE');
    return new Promise((resolve) => {
      this.socket.end(() => resolve());
    });
  }

  setTimeout(ms) {
    this.socket.setTimeout(ms);
  }
}

// Monkey-patch the client to use our proxy
function createProxiedClient(host, port, logger) {
  const client = new IconaBridgeClient(host, port, logger);
  
  // Override connect to inject our proxy
  const originalConnect = client.connect.bind(client);
  client.connect = async function() {
    this._socket = new net.Socket();
    this.socket = new SocketProxy(this._socket, logger);
    this.socket.setTimeout(5000);
    logger.info(`Connecting to ${this.host}:${this.port}`);
    await this.socket.connect(this.port, this.host);
    this.socket.socket.setMaxListeners(40);
    logger.info('connected');
  };
  
  return client;
}

// Run protocol tests
async function captureProtocol() {
  const logger = new ProtocolLogger('comelit-protocol-capture');
  
  try {
    logger.info('Starting protocol capture', { 
      host: COMELIT_IP, 
      port: ICONA_BRIDGE_PORT 
    });

    const client = createProxiedClient(COMELIT_IP, ICONA_BRIDGE_PORT, logger);
    
    // Connect to the device
    await client.connect();
    
    // Authenticate
    logger.info('Authenticating...');
    const authCode = await client.authenticate(COMELIT_TOKEN);
    logger.info('Authentication result', { code: authCode });
    
    if (authCode === 200) {
      // Get server info
      logger.info('Getting server info...');
      const serverInfo = await client.getServerInfo();
      logger.info('Server info', { serverInfo });
      
      // Get configuration
      logger.info('Getting configuration (all)...');
      const configAll = await client.getConfig('all');
      logger.info('Configuration', { config: configAll });
      
      // List available doors
      if (configAll?.vip?.['user-parameters']?.['opendoor-address-book']) {
        const doors = configAll.vip['user-parameters']['opendoor-address-book'];
        logger.info('Available doors', { doors });
        
        // If there's at least one door, simulate opening it
        if (doors.length > 0) {
          const door = doors[0];
          logger.info('Simulating door open', { door });
          
          // This will capture all the binary protocol messages
          await client.openDoor(configAll.vip, door);
          
          logger.info('Door open sequence completed');
        }
      }
    }
    
    // Shutdown
    await client.shutdown();
    logger.info('Client shutdown complete');
    
  } catch (error) {
    logger.error('Error during protocol capture', { 
      error: error.message,
      stack: error.stack 
    });
  } finally {
    logger.save();
  }
}

// Run the capture
captureProtocol().catch(console.error);
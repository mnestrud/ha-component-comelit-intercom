import { IconaBridgeClient, ICONA_BRIDGE_PORT } from 'comelit-client';
import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

// Test configuration
const COMELIT_IP = process.env.COMELIT_IP_ADDRESS || '10.0.1.49';
const COMELIT_TOKEN = process.env.COMELIT_TOKEN || '9943a85362467c53586e3553d34f8a8d';

// Create output directory
const outputDir = path.join(process.cwd(), 'protocol-comparison');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

// Capture logger for JS implementation
class CaptureLogger {
  constructor(name) {
    this.name = name;
    this.logs = [];
  }

  _log(level, message, data) {
    const entry = {
      timestamp: Date.now(),
      level,
      message: typeof message === 'object' ? JSON.stringify(message) : message,
      data
    };
    this.logs.push(entry);
    console.log(`[${this.name}] ${level}: ${entry.message}`);
  }

  log(msg, data) { this._log('log', msg, data); }
  info(msg, data) { this._log('info', msg, data); }
  debug(msg, data) { this._log('debug', msg, data); }
  warn(msg, data) { this._log('warn', msg, data); }
  error(msg, data) { this._log('error', msg, data); }

  save(filename) {
    const filepath = path.join(outputDir, filename);
    fs.writeFileSync(filepath, JSON.stringify(this.logs, null, 2));
    console.log(`Logs saved to: ${filepath}`);
  }
}

// Socket interceptor to capture raw protocol data
class SocketInterceptor {
  constructor(socket, logger) {
    this.socket = socket;
    this.logger = logger;
    this.packets = [];
    
    // Intercept write
    const originalWrite = socket.write.bind(socket);
    socket.write = (data, encoding, callback) => {
      this.packets.push({
        direction: 'send',
        timestamp: Date.now(),
        data: data.toString('hex'),
        ascii: data.toString('ascii').replace(/[\x00-\x1F\x7F-\xFF]/g, '.')
      });
      return originalWrite(data, encoding, callback);
    };
    
    // Intercept data events
    socket.on('data', (data) => {
      this.packets.push({
        direction: 'receive',
        timestamp: Date.now(),
        data: data.toString('hex'),
        ascii: data.toString('ascii').replace(/[\x00-\x1F\x7F-\xFF]/g, '.')
      });
    });
  }

  save(filename) {
    const filepath = path.join(outputDir, filename);
    fs.writeFileSync(filepath, JSON.stringify(this.packets, null, 2));
    console.log(`Packets saved to: ${filepath}`);
  }
}

// Test the JavaScript implementation
async function testJavaScriptImplementation() {
  console.log('\n=== Testing JavaScript Implementation ===\n');
  
  const logger = new CaptureLogger('JS');
  const client = new IconaBridgeClient(COMELIT_IP, ICONA_BRIDGE_PORT, logger);
  let interceptor = null;
  
  try {
    // Connect and intercept socket
    await client.connect();
    interceptor = new SocketInterceptor(client._socket, logger);
    
    // Authenticate
    console.log('Authenticating...');
    const authCode = await client.authenticate(COMELIT_TOKEN);
    console.log(`Auth result: ${authCode}`);
    
    if (authCode === 200) {
      // Get configuration
      console.log('Getting configuration...');
      const config = await client.getConfig('all');
      
      // Extract doors
      const doors = config?.vip?.['user-parameters']?.['opendoor-address-book'] || [];
      console.log(`Found ${doors.length} doors`);
      
      // Save door list
      fs.writeFileSync(
        path.join(outputDir, 'js-doors.json'),
        JSON.stringify(doors, null, 2)
      );
      
      // If there's a door, test opening it
      if (doors.length > 0) {
        const door = doors[0];
        console.log(`Opening door: ${door.name}`);
        await client.openDoor(config.vip, door);
        console.log('Door opened');
      }
    }
    
    await client.shutdown();
    
  } catch (error) {
    logger.error('Error in JS implementation', { error: error.message });
    console.error('JS Error:', error);
  } finally {
    if (interceptor) {
      interceptor.save('js-packets.json');
    }
    logger.save('js-logs.json');
  }
}

// Test the Python implementation
async function testPythonImplementation() {
  console.log('\n=== Testing Python Implementation ===\n');
  
  return new Promise((resolve, reject) => {
    const pythonScript = `
import asyncio
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from comelit_client_python import list_doors, open_door, IconaBridgeClient
import logging

# Configure logging to capture protocol details
class JsonLogger(logging.Handler):
    def __init__(self):
        super().__init__()
        self.logs = []
        
    def emit(self, record):
        self.logs.append({
            'timestamp': int(record.created * 1000),
            'level': record.levelname.lower(),
            'message': record.getMessage()
        })

async def test():
    host = os.getenv('COMELIT_IP_ADDRESS', '10.0.1.49')
    token = os.getenv('COMELIT_TOKEN', '9943a85362467c53586e3553d34f8a8d')
    
    # Set up logging
    logger = logging.getLogger('comelit_client_python')
    logger.setLevel(logging.DEBUG)
    json_handler = JsonLogger()
    logger.addHandler(json_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter('[PY] %(levelname)s: %(message)s'))
    logger.addHandler(console_handler)
    
    try:
        # List doors
        print('Listing doors...')
        doors = await list_doors(host, token)
        print(f'Found {len(doors)} doors')
        
        # Save doors
        with open('protocol-comparison/py-doors.json', 'w') as f:
            json.dump(doors, f, indent=2)
        
        # Open first door if available
        if doors:
            door_name = doors[0].get('name')
            print(f'Opening door: {door_name}')
            await open_door(host, token, door_name)
            print('Door opened')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        # Save logs
        with open('protocol-comparison/py-logs.json', 'w') as f:
            json.dump(json_handler.logs, f, indent=2)

asyncio.run(test())
`;

    // Write Python test script
    const scriptPath = path.join(process.cwd(), 'test_python_impl.py');
    fs.writeFileSync(scriptPath, pythonScript);
    
    // Run Python script
    const pythonProcess = spawn('python3', [scriptPath], {
      env: { ...process.env },
      cwd: process.cwd()
    });
    
    pythonProcess.stdout.on('data', (data) => {
      process.stdout.write(data);
    });
    
    pythonProcess.stderr.on('data', (data) => {
      process.stderr.write(data);
    });
    
    pythonProcess.on('close', (code) => {
      // Clean up
      fs.unlinkSync(scriptPath);
      
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`Python process exited with code ${code}`));
      }
    });
  });
}

// Compare the results
function compareImplementations() {
  console.log('\n=== Comparing Implementations ===\n');
  
  try {
    // Load door lists
    const jsDoors = JSON.parse(fs.readFileSync(path.join(outputDir, 'js-doors.json'), 'utf8'));
    const pyDoors = JSON.parse(fs.readFileSync(path.join(outputDir, 'py-doors.json'), 'utf8'));
    
    // Compare door counts
    console.log(`JavaScript found ${jsDoors.length} doors`);
    console.log(`Python found ${pyDoors.length} doors`);
    
    if (jsDoors.length === pyDoors.length) {
      console.log('✓ Door count matches');
      
      // Compare door details
      for (let i = 0; i < jsDoors.length; i++) {
        const jsDoor = jsDoors[i];
        const pyDoor = pyDoors[i];
        
        console.log(`\nComparing door ${i + 1}:`);
        console.log(`  JS: ${jsDoor.name} (address: ${jsDoor['apt-address']})`);
        console.log(`  PY: ${pyDoor.name} (address: ${pyDoor['apt-address']})`);
        
        if (jsDoor.name === pyDoor.name && 
            jsDoor['apt-address'] === pyDoor['apt-address'] &&
            jsDoor['output-index'] === pyDoor['output-index']) {
          console.log('  ✓ Door details match');
        } else {
          console.log('  ✗ Door details differ');
        }
      }
    } else {
      console.log('✗ Door count differs');
    }
    
    // Compare packet patterns (if available)
    if (fs.existsSync(path.join(outputDir, 'js-packets.json'))) {
      const jsPackets = JSON.parse(fs.readFileSync(path.join(outputDir, 'js-packets.json'), 'utf8'));
      console.log(`\nJavaScript sent ${jsPackets.filter(p => p.direction === 'send').length} packets`);
      console.log(`JavaScript received ${jsPackets.filter(p => p.direction === 'receive').length} packets`);
    }
    
  } catch (error) {
    console.error('Error comparing implementations:', error);
  }
}

// Main test runner
async function runComparison() {
  console.log('Comelit Client Implementation Comparison');
  console.log('========================================');
  console.log(`Target: ${COMELIT_IP}`);
  
  try {
    // Test both implementations
    await testJavaScriptImplementation();
    await testPythonImplementation();
    
    // Compare results
    compareImplementations();
    
    console.log('\n✓ Comparison complete. Check protocol-comparison/ directory for detailed results.');
    
  } catch (error) {
    console.error('\nTest failed:', error);
  }
}

// Run the comparison
runComparison().catch(console.error);
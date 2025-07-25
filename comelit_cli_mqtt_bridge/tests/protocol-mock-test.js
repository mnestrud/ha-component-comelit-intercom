import fs from 'fs';
import path from 'path';

// Based on analysis of the comelit-client library, create a mock protocol capture
// This demonstrates the expected protocol flow for future Python implementation

const mockCapture = {
  operations: [],
  startTime: 0
};

function addOperation(level, message, data = {}) {
  mockCapture.operations.push({
    timestamp: mockCapture.operations.length * 100,
    level,
    message,
    ...data
  });
}

// Simulate the protocol flow based on the library code

// 1. Connection
addOperation('info', 'CONNECT', { port: 64100, host: '10.0.1.49' });
addOperation('info', 'CONNECTED', { port: 64100, host: '10.0.1.49' });

// 2. Open UAUT channel for authentication
addOperation('WRITE', 'Open UAUT channel', {
  operationId: 1,
  bytes: '00 06 0c 00 01 20 00 00 cd ab 01 00 08 00 00 00 55 41 55 54 00 01 20 00',
  length: 24,
  ascii: '.......... ......UAUT.. .',
  comment: 'COMMAND message (0xabcd) with sequence 1, channel UAUT'
});

addOperation('READ', 'UAUT channel response', {
  operationId: 1,
  bytes: '00 06 04 00 00 00 00 00 cd ab 02 00',
  length: 12,
  ascii: '................',
  comment: 'Channel opened, sequence 2'
});

// 3. Send authentication message (JSON)
const authJson = {
  message: 'access',
  'user-token': '9943a85362467c53586e3553d34f8a8d',
  'message-type': 'request',
  'message-id': 2  // UAUT
};
const authJsonStr = JSON.stringify(authJson);
const authJsonHex = Buffer.from(authJsonStr).toString('hex').match(/.{1,2}/g).join(' ');

addOperation('WRITE', 'Authentication request', {
  operationId: 2,
  bytes: `00 06 ${authJsonStr.length.toString(16).padStart(2, '0')} 00 01 20 00 00 ${authJsonHex}`,
  length: 8 + authJsonStr.length,
  ascii: `......${authJsonStr}`,
  comment: 'JSON authentication message'
});

addOperation('READ', 'Authentication response', {
  operationId: 2,
  bytes: '00 06 2a 00 01 20 00 00 7b 22 72 65 73 70 6f 6e 73 65 2d 63 6f 64 65 22 3a 32 30 30 2c 22 6d 65 73 73 61 67 65 2d 74 79 70 65 22 3a 22 72 65 73 70 6f 6e 73 65 22 7d',
  length: 50,
  ascii: '......*... .{"response-code":200,"message-type":"response"}',
  comment: 'Authentication successful'
});

// 4. Close UAUT channel
addOperation('WRITE', 'Close UAUT channel', {
  operationId: 3,
  bytes: '00 06 04 00 01 20 00 00 ef 01 03 00',
  length: 12,
  ascii: '.......... ...',
  comment: 'END message (0x01ef) with sequence 3'
});

// 5. Open UCFG channel for configuration
addOperation('WRITE', 'Open UCFG channel', {
  operationId: 4,
  bytes: '00 06 0c 00 02 20 00 00 cd ab 01 00 08 00 00 00 55 43 46 47 00 02 20 00',
  length: 24,
  ascii: '.......... ......UCFG.. .',
  comment: 'COMMAND message with channel UCFG'
});

// 6. Get configuration
const configJson = {
  message: 'get-configuration',
  addressbooks: 'all',
  'message-type': 'request',
  'message-id': 3  // UCFG
};
const configJsonStr = JSON.stringify(configJson);
const configJsonHex = Buffer.from(configJsonStr).toString('hex').match(/.{1,2}/g).join(' ');

addOperation('WRITE', 'Get configuration request', {
  operationId: 5,
  bytes: `00 06 ${configJsonStr.length.toString(16).padStart(2, '0')} 00 02 20 00 00 ${configJsonHex}`,
  length: 8 + configJsonStr.length,
  ascii: `......${configJsonStr}`,
  comment: 'JSON get-configuration message'
});

// 7. Open door sequence (binary protocol)
// First open CTPP channel
addOperation('WRITE', 'Open CTPP channel', {
  operationId: 6,
  bytes: '00 06 14 00 03 20 00 00 cd ab 01 00 0c 00 00 00 43 54 50 50 00 03 20 31 30 30 31 00',
  length: 28,
  ascii: '.......... ......CTPP.. 1001.',
  comment: 'COMMAND message with channel CTPP and apartment address'
});

// Init door open
addOperation('WRITE', 'Init door open', {
  operationId: 7,
  bytes: '00 06 1c 00 03 20 00 00 c0 18 5c 8b 2b 73 00 11 00 40 ac 23 31 30 30 31 00 10 0e 00 00 00 00 ff ff ff ff 31 30 30 31 00 31 30 30 00',
  length: 44,
  ascii: '.......... ...\\+s...@.#1001......1001.100.',
  comment: 'Binary door init message'
});

// Open door command
addOperation('WRITE', 'Open door command', {
  operationId: 8,
  bytes: '00 06 18 00 03 20 00 00 00 18 5c 8b 2c 74 00 00 ff ff ff ff 31 30 30 31 31 00 31 30 30 00',
  length: 32,
  ascii: '.......... ..\\.,t....10011.100.',
  comment: 'Binary open door message (0x1800)'
});

// Open door confirm
addOperation('WRITE', 'Open door confirm', {
  operationId: 9,
  bytes: '00 06 18 00 03 20 00 00 20 18 5c 8b 2c 74 00 00 ff ff ff ff 31 30 30 31 31 00 31 30 30 00',
  length: 32,
  ascii: '.......... ..\\.,t....10011.100.',
  comment: 'Binary open door confirm (0x1820)'
});

// Save mock capture
const outputDir = path.join(process.cwd(), 'protocol-captures');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const outputFile = path.join(outputDir, 'comelit-protocol-mock.json');
fs.writeFileSync(outputFile, JSON.stringify(mockCapture.operations, null, 2));

console.log(`Mock protocol capture saved to: ${outputFile}`);
console.log('\nProtocol Summary:');
console.log('1. Connect to device on port 64100');
console.log('2. Open channel with COMMAND message (0xabcd)');
console.log('3. Send JSON messages for auth/config');
console.log('4. Use binary protocol for door operations');
console.log('5. Close channels with END message (0x01ef)');
console.log('\nKey insights:');
console.log('- 8-byte header: 00 06 <size:2> <request_id:2> 00 00');
console.log('- JSON messages start with 0x7b ({)');
console.log('- Binary messages use specific message types');
console.log('- Channels must be opened before use');
console.log('- Door operations use complex binary protocol');
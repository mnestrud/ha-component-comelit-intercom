import { IconaBridgeClient } from 'comelit-client';

async function testRealDevice() {
    const client = new IconaBridgeClient('10.0.1.49');
    
    try {
        console.log('Connecting to Comelit device at 10.0.1.49...');
        await client.connect();
        console.log('Connected!');
        
        console.log('Authenticating with token...');
        const authCode = await client.authenticate('9943a85362467c53586e3553d34f8a8d');
        console.log('Authentication result:', authCode);
        
        if (authCode === 200) {
            console.log('Authentication successful! Getting config...');
            const config = await client.getConfig('all');
            console.log('Config received:', JSON.stringify(config, null, 2));
            
            console.log('\nListing doors...');
            const doors = await client.listDoors();
            console.log('Doors:', doors);
        } else {
            console.log('Authentication failed with code:', authCode);
        }
        
        await client.shutdown();
        console.log('Connection closed');
        
    } catch (error) {
        console.error('Error:', error);
    }
}

testRealDevice().catch(console.error);
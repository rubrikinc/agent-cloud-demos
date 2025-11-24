#!/usr/bin/env node

/**
 * Test SQL Server Connection
 * 
 * This script tests the database connection using the same logic as the MCP server
 * to help diagnose connection issues.
 */

const sql = require('mssql');
const dotenv = require('dotenv');

// Load environment variables
dotenv.config();

/**
 * Parse ODBC connection string into key-value pairs
 */
function parseOdbcConnectionString(connectionString) {
  const params = {};
  const parts = connectionString.split(';').filter(part => part.trim());
  
  for (const part of parts) {
    const equalIndex = part.indexOf('=');
    if (equalIndex > 0) {
      const key = part.substring(0, equalIndex).trim();
      const value = part.substring(equalIndex + 1).trim();
      params[key] = value;
    }
  }
  
  return params;
}

/**
 * Convert ODBC connection string to mssql config object
 */
function odbcToMssqlConfig(connectionString) {
  const params = parseOdbcConnectionString(connectionString);
  
  // Extract common parameters (case-insensitive lookup)
  const getParam = (keys) => {
    for (const key of keys) {
      const value = Object.keys(params).find(k => k.toLowerCase() === key.toLowerCase());
      if (value) return params[value];
    }
    return undefined;
  };
  
  const server = getParam(['Server', 'Data Source', 'Address', 'Addr', 'Network Address']);
  const database = getParam(['Database', 'Initial Catalog']);
  const user = getParam(['UID', 'User ID', 'User']);
  const password = getParam(['PWD', 'Password']);
  const trustedConnection = getParam(['Trusted_Connection', 'Integrated Security'])?.toLowerCase() === 'yes' ||
                           getParam(['Trusted_Connection', 'Integrated Security'])?.toLowerCase() === 'true';
  const encrypt = getParam(['Encrypt'])?.toLowerCase() !== 'no' && getParam(['Encrypt'])?.toLowerCase() !== 'false';
  const trustServerCert = getParam(['TrustServerCertificate'])?.toLowerCase() === 'yes' ||
                         getParam(['TrustServerCertificate'])?.toLowerCase() === 'true';
  const connectionTimeout = getParam(['Connection Timeout', 'Connect Timeout']);
  
  if (!server) {
    throw new Error('ODBC connection string must contain Server parameter');
  }
  
  const config = {
    server: server,
    options: {
      encrypt: encrypt,
      trustServerCertificate: trustServerCert,
    },
  };
  
  if (database) {
    config.database = database;
  }
  
  if (connectionTimeout) {
    config.connectionTimeout = parseInt(connectionTimeout, 10) * 1000; // convert to milliseconds
  }
  
  // Authentication: SQL or Windows
  if (user && password) {
    // SQL Server authentication
    config.user = user;
    config.password = password;
  } else if (trustedConnection) {
    // Windows authentication
    config.authentication = {
      type: 'ntlm',
      options: {
        domain: '',
        userName: '',
        password: '',
      },
    };
  }
  
  return config;
}

async function testConnection() {
  console.log('='*80);
  console.log('SQL Server Connection Test');
  console.log('='*80);
  
  // Check for ODBC connection string
  const odbcConnectionString = process.env.MSSQL_CONNECTION_STRING;
  
  if (!odbcConnectionString) {
    console.error('❌ Error: MSSQL_CONNECTION_STRING environment variable not set');
    console.error('   Please set it in your .env file');
    process.exit(1);
  }
  
  console.log('\n✓ MSSQL_CONNECTION_STRING found');
  console.log(`  Value: ${odbcConnectionString.substring(0, 50)}...`);
  
  try {
    console.log('\n📋 Parsing ODBC connection string...');
    const config = odbcToMssqlConfig(odbcConnectionString);
    
    console.log('\n✓ Parsed configuration:');
    console.log(`  Server: ${config.server}`);
    console.log(`  Database: ${config.database}`);
    console.log(`  User: ${config.user}`);
    console.log(`  Password: ${config.password ? '***' : 'Not set'}`);
    console.log(`  Encrypt: ${config.options.encrypt}`);
    console.log(`  TrustServerCertificate: ${config.options.trustServerCertificate}`);
    console.log(`  ConnectionTimeout: ${config.connectionTimeout}ms`);
    
    console.log('\n🔌 Attempting to connect to SQL Server...');
    console.log('   (This may take up to 30 seconds)');
    
    const pool = await sql.connect(config);
    
    console.log('\n✅ SUCCESS: Connected to SQL Server!');
    
    console.log('\n📊 Testing query: SELECT @@VERSION');
    const result = await pool.request().query('SELECT @@VERSION AS version');
    console.log(`   Result: ${result.recordset[0].version.substring(0, 100)}...`);
    
    console.log('\n📊 Listing tables...');
    const tables = await pool.request().query(`
      SELECT TABLE_SCHEMA, TABLE_NAME 
      FROM INFORMATION_SCHEMA.TABLES 
      WHERE TABLE_TYPE = 'BASE TABLE'
      ORDER BY TABLE_SCHEMA, TABLE_NAME
    `);
    
    console.log(`   Found ${tables.recordset.length} tables:`);
    tables.recordset.forEach(table => {
      console.log(`   - ${table.TABLE_SCHEMA}.${table.TABLE_NAME}`);
    });
    
    await pool.close();
    console.log('\n✅ Connection test completed successfully!');
    
  } catch (error) {
    console.error('\n❌ ERROR: Failed to connect to SQL Server');
    console.error(`   ${error.message}`);
    console.error('\nPossible causes:');
    console.error('1. Incorrect server name or port');
    console.error('2. Incorrect username or password');
    console.error('3. Firewall blocking the connection');
    console.error('4. SQL Server not accepting remote connections');
    console.error('5. Database does not exist');
    console.error('\nFull error:');
    console.error(error);
    process.exit(1);
  }
}

testConnection();


#!/usr/bin/env node

// External imports
import * as dotenv from "dotenv";
import sql from "mssql";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Internal imports
import { UpdateDataTool } from "./tools/UpdateDataTool.js";
import { InsertDataTool } from "./tools/InsertDataTool.js";
import { ReadDataTool } from "./tools/ReadDataTool.js";
import { CreateTableTool } from "./tools/CreateTableTool.js";
import { CreateIndexTool } from "./tools/CreateIndexTool.js";
import { ListTableTool } from "./tools/ListTableTool.js";
import { DropTableTool } from "./tools/DropTableTool.js";
import { DefaultAzureCredential, InteractiveBrowserCredential } from "@azure/identity";
import { DescribeTableTool } from "./tools/DescribeTableTool.js";

// MSSQL Database connection configuration
// const credential = new DefaultAzureCredential();

// Globals for connection and token reuse
let globalSqlPool: sql.ConnectionPool | null = null;
let globalAccessToken: string | null = null;
let globalTokenExpiresOn: Date | null = null;

/**
 * Parse ODBC connection string into key-value pairs
 * Example: "Server=localhost;Database=mydb;UID=user;PWD=pass;"
 * Returns: { Server: "localhost", Database: "mydb", UID: "user", PWD: "pass" }
 */
function parseOdbcConnectionString(connectionString: string): Record<string, string> {
  const params: Record<string, string> = {};

  // Split by semicolon and process each key=value pair
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
function odbcToMssqlConfig(connectionString: string): sql.config {
  const params = parseOdbcConnectionString(connectionString);

  // Extract common parameters (case-insensitive lookup)
  const getParam = (keys: string[]): string | undefined => {
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

  const config: sql.config = {
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

// Function to create SQL config with fresh access token, returns token and expiry
export async function createSqlConfig(): Promise<{ config: sql.config, token: string | null, expiresOn: Date | null }> {
  // Priority 1: Check for ODBC connection string (supports SQL authentication)
  const odbcConnectionString = process.env.MSSQL_CONNECTION_STRING;

  if (odbcConnectionString) {
    console.error('[MCP Server] Using ODBC connection string for SQL authentication');

    try {
      const config = odbcToMssqlConfig(odbcConnectionString);
      return {
        config,
        token: null,
        expiresOn: null
      };
    } catch (error) {
      console.error('[MCP Server] Error parsing ODBC connection string:', error);
      throw error;
    }
  }

  // Priority 2: Check for SQL username/password authentication
  const sqlUser = process.env.SQL_USER;
  const sqlPassword = process.env.SQL_PASSWORD;

  if (sqlUser && sqlPassword) {
    console.error(`[MCP Server] Using SQL Server authentication for user: ${sqlUser}`);

    const trustServerCertificate = process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true';
    const connectionTimeout = process.env.CONNECTION_TIMEOUT ? parseInt(process.env.CONNECTION_TIMEOUT, 10) : 30;

    return {
      config: {
        server: process.env.SERVER_NAME!,
        database: process.env.DATABASE_NAME!,
        user: sqlUser,
        password: sqlPassword,
        options: {
          encrypt: true,
          trustServerCertificate
        },
        connectionTimeout: connectionTimeout * 1000,
      },
      token: null,
      expiresOn: null
    };
  }

  // Priority 3: Fall back to Azure AD authentication (original behavior)
  console.error('[MCP Server] Using Azure AD Interactive Browser authentication');

  const credential = new InteractiveBrowserCredential({
    redirectUri: 'http://localhost'
    // disableAutomaticAuthentication : true
  });
  const accessToken = await credential.getToken('https://database.windows.net/.default');

  const trustServerCertificate = process.env.TRUST_SERVER_CERTIFICATE?.toLowerCase() === 'true';
  const connectionTimeout = process.env.CONNECTION_TIMEOUT ? parseInt(process.env.CONNECTION_TIMEOUT, 10) : 30;

  return {
    config: {
      server: process.env.SERVER_NAME!,
      database: process.env.DATABASE_NAME!,
      options: {
        encrypt: true,
        trustServerCertificate
      },
      authentication: {
        type: 'azure-active-directory-access-token',
        options: {
          token: accessToken?.token!,
        },
      },
      connectionTimeout: connectionTimeout * 1000, // convert seconds to milliseconds
    },
    token: accessToken?.token!,
    expiresOn: accessToken?.expiresOnTimestamp ? new Date(accessToken.expiresOnTimestamp) : new Date(Date.now() + 30 * 60 * 1000)
  };
}

const updateDataTool = new UpdateDataTool();
const insertDataTool = new InsertDataTool();
const readDataTool = new ReadDataTool();
const createTableTool = new CreateTableTool();
const createIndexTool = new CreateIndexTool();
const listTableTool = new ListTableTool();
const dropTableTool = new DropTableTool();
const describeTableTool = new DescribeTableTool();

const server = new Server(
  {
    name: "mssql-mcp-server",
    version: "0.1.0",
  },
  {
    capabilities: {
      tools: {},
    },
  },
);

// Read READONLY env variable
const isReadOnly = process.env.READONLY === "true";

// Request handlers

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: isReadOnly
    ? [listTableTool, readDataTool, describeTableTool] // todo: add searchDataTool to the list of tools available in readonly mode once implemented
    : [insertDataTool, readDataTool, describeTableTool, updateDataTool, createTableTool, createIndexTool, dropTableTool, listTableTool], // add all new tools here
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  try {
    let result;
    switch (name) {
      case insertDataTool.name:
        result = await insertDataTool.run(args);
        break;
      case readDataTool.name:
        result = await readDataTool.run(args);
        break;
      case updateDataTool.name:
        result = await updateDataTool.run(args);
        break;
      case createTableTool.name:
        result = await createTableTool.run(args);
        break;
      case createIndexTool.name:
        result = await createIndexTool.run(args);
        break;
      case listTableTool.name:
        result = await listTableTool.run(args);
        break;
      case dropTableTool.name:
        result = await dropTableTool.run(args);
        break;
      case describeTableTool.name:
        if (!args || typeof args.tableName !== "string") {
          return {
            content: [{ type: "text", text: `Missing or invalid 'tableName' argument for describe_table tool.` }],
            isError: true,
          };
        }
        result = await describeTableTool.run(args as { tableName: string });
        break;
      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (error) {
    return {
      content: [{ type: "text", text: `Error occurred: ${error}` }],
      isError: true,
    };
  }
});

// Server startup
async function runServer() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
  } catch (error) {
    console.error("Fatal error running server:", error);
    process.exit(1);
  }
}

runServer().catch((error) => {
  console.error("Fatal error running server:", error);
  process.exit(1);
});

// Connect to SQL only when handling a request

async function ensureSqlConnection() {
  // Check if using SQL authentication (no token) or Azure AD (with token)
  const usingSqlAuth = process.env.MSSQL_CONNECTION_STRING ||
                       (process.env.SQL_USER && process.env.SQL_PASSWORD);

  if (usingSqlAuth) {
    // SQL authentication - just check if pool is connected
    if (globalSqlPool && globalSqlPool.connected) {
      return;
    }

    // Create new connection
    const { config } = await createSqlConfig();

    // Close old pool if exists
    if (globalSqlPool && globalSqlPool.connected) {
      await globalSqlPool.close();
    }

    globalSqlPool = await sql.connect(config);
  } else {
    // Azure AD authentication - check token expiry
    if (
      globalSqlPool &&
      globalSqlPool.connected &&
      globalAccessToken &&
      globalTokenExpiresOn &&
      globalTokenExpiresOn > new Date(Date.now() + 2 * 60 * 1000) // 2 min buffer
    ) {
      return;
    }

    // Get a new token and reconnect
    const { config, token, expiresOn } = await createSqlConfig();
    globalAccessToken = token;
    globalTokenExpiresOn = expiresOn;

    // Close old pool if exists
    if (globalSqlPool && globalSqlPool.connected) {
      await globalSqlPool.close();
    }

    globalSqlPool = await sql.connect(config);
  }
}

// Patch all tool handlers to ensure SQL connection before running
function wrapToolRun(tool: { run: (...args: any[]) => Promise<any> }) {
  const originalRun = tool.run.bind(tool);
  tool.run = async function (...args: any[]) {
    await ensureSqlConnection();
    return originalRun(...args);
  };
}

[insertDataTool, readDataTool, updateDataTool, createTableTool, createIndexTool, dropTableTool, listTableTool, describeTableTool].forEach(wrapToolRun);
const writeToStdOut = (logLevel, message, ...optionalParams) => {
  if (!message || message === "") {
    return;
  }
  
  const timestamp = (new Date).toISOString();
  const logLinePrefix = `[${timestamp} - ${logLevel}] `;

  if (typeof(message) === 'object') {
    console[logLevel](logLinePrefix, message, ...optionalParams);
  } else {
    console[logLevel](`${logLinePrefix} ${message}`, ...optionalParams);
  }
}

const debug = (_message, ..._optionalParams) => undefined; // Debug logs are being ignored

const log = (message, ...optionalParams) => writeToStdOut('log', message, ...optionalParams);
const info = (message, ...optionalParams) => writeToStdOut('info', message, ...optionalParams);
const warn = (message, ...optionalParams) => writeToStdOut('warn', message, ...optionalParams);
const error = (message, ...optionalParams) => writeToStdOut('error', message, ...optionalParams);

export const logger = {
  log,
  debug,
  info,
  warn,
  error
}

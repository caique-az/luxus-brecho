import { CONFIG } from '../constants/config';

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

export interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  context?: string;
  meta?: Record<string, unknown>;
  error?: Error;
}

class Logger {
  private currentLevel: LogLevel = __DEV__ ? LogLevel.DEBUG : LogLevel.INFO;
  private logs: LogEntry[] = [];
  private maxLogs = 1000;

  private shouldLog(level: LogLevel): boolean {
    return level >= this.currentLevel && CONFIG.DEBUG.ENABLE_LOGS;
  }

  private createLogEntry(
    level: LogLevel,
    message: string,
    context?: string,
    meta?: Record<string, unknown>,
    error?: Error
  ): LogEntry {
    return {
      level,
      message,
      timestamp: new Date().toISOString(),
      context,
      meta,
      error,
    };
  }

  private addLog(entry: LogEntry): void {
    this.logs.push(entry);
    
    // Manter apenas os últimos logs
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }
  }

  private formatMessage(entry: LogEntry): string {
    const levelStr = LogLevel[entry.level];
    const contextStr = entry.context ? `[${entry.context}]` : '';
    const metaStr = entry.meta ? JSON.stringify(entry.meta) : '';
    
    return `${entry.timestamp} ${levelStr} ${contextStr} ${entry.message} ${metaStr}`;
  }

  debug(message: string, context?: string, meta?: Record<string, unknown>): void {
    if (!this.shouldLog(LogLevel.DEBUG)) return;
    
    const entry = this.createLogEntry(LogLevel.DEBUG, message, context, meta);
    this.addLog(entry);
    
    if (__DEV__) {
      console.log(`🐛 ${this.formatMessage(entry)}`);
    }
  }

  info(message: string, context?: string, meta?: Record<string, unknown>): void {
    if (!this.shouldLog(LogLevel.INFO)) return;
    
    const entry = this.createLogEntry(LogLevel.INFO, message, context, meta);
    this.addLog(entry);
    
    if (__DEV__) {
      console.info(`ℹ️ ${this.formatMessage(entry)}`);
    }
  }

  warn(message: string, context?: string, meta?: Record<string, unknown>): void {
    if (!this.shouldLog(LogLevel.WARN)) return;
    
    const entry = this.createLogEntry(LogLevel.WARN, message, context, meta);
    this.addLog(entry);
    
    console.warn(`⚠️ ${this.formatMessage(entry)}`);
  }

  error(message: string, error?: Error, context?: string, meta?: Record<string, unknown>): void {
    if (!this.shouldLog(LogLevel.ERROR)) return;
    
    const entry = this.createLogEntry(LogLevel.ERROR, message, context, meta, error);
    this.addLog(entry);
    
    console.error(`❌ ${this.formatMessage(entry)}`, error);
  }

  // Métodos utilitários
  getLogs(level?: LogLevel): LogEntry[] {
    if (level !== undefined) {
      return this.logs.filter(log => log.level >= level);
    }
    return [...this.logs];
  }

  clearLogs(): void {
    this.logs = [];
  }

  setLevel(level: LogLevel): void {
    this.currentLevel = level;
  }

  // Métodos específicos para contextos comuns
  api(message: string, meta?: Record<string, unknown>): void {
    this.info(message, 'API', meta);
  }

  auth(message: string, meta?: Record<string, unknown>): void {
    this.info(message, 'AUTH', meta);
  }

  navigation(message: string, meta?: Record<string, unknown>): void {
    this.debug(message, 'NAVIGATION', meta);
  }

  cache(message: string, meta?: Record<string, unknown>): void {
    if (CONFIG.DEBUG.ENABLE_CACHE_LOGS) {
      this.debug(message, 'CACHE', meta);
    }
  }

  performance(message: string, meta?: Record<string, unknown>): void {
    this.info(message, 'PERFORMANCE', meta);
  }
}

// Instância singleton
export const logger = new Logger();

// Interceptar erros globais não tratados
if (__DEV__) {
  const originalConsoleError = console.error;
  console.error = (...args: unknown[]) => {
    originalConsoleError.apply(console, args);
  };
}

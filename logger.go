package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/sirupsen/logrus"
	"gopkg.in/yaml.v3"
)

type LogLevel string

const (
	DEBUG LogLevel = "DEBUG"
	INFO  LogLevel = "INFO"
	WARN  LogLevel = "WARN"
	ERROR LogLevel = "ERROR"
	FATAL LogLevel = "FATAL"
)

type LogFormat string

const (
	TEXT LogFormat = "text"
	JSON LogFormat = "json"
)

type LogConfig struct {
	Level      LogLevel   `yaml:"level" json:"level"`
	Format     LogFormat  `yaml:"format" json:"format"`
	Output     string     `yaml:"output" json:"output"`
	Rotation   bool       `yaml:"rotation" json:"rotation"`
	MaxSize    int64      `yaml:"max_size" json:"max_size"`    // MB
	MaxFiles   int        `yaml:"max_files" json:"max_files"`
	Compress   bool       `yaml:"compress" json:"compress"`
	Fields     map[string]interface{} `yaml:"fields" json:"fields"`
}

type LogEntry struct {
	Timestamp time.Time              `json:"timestamp"`
	Level     LogLevel               `json:"level"`
	Message   string                 `json:"message"`
	Fields    map[string]interface{} `json:"fields,omitempty"`
	Source    string                 `json:"source"`
	Function  string                 `json:"function,omitempty"`
	Line      int                    `json:"line,omitempty"`
}

type Logger struct {
	config      LogConfig
	logrus      *logrus.Logger
	file        *os.File
	mu          sync.RWMutex
	rotator     *LogRotator
}

type LogRotator struct {
	config      LogConfig
	currentSize int64
	fileCount   int
	mu          sync.Mutex
}

func NewLogger(config LogConfig) (*Logger, error) {
	logger := &Logger{
		config: config,
		logrus: logrus.New(),
	}

	// Set log level
	level, err := logrus.ParseLevel(string(config.Level))
	if err != nil {
		level = logrus.InfoLevel
	}
	logger.logrus.SetLevel(level)

	// Set formatter
	if config.Format == JSON {
		logger.logrus.SetFormatter(&logrus.JSONFormatter{
			TimestampFormat: time.RFC3339,
		})
	} else {
		logger.logrus.SetFormatter(&logrus.TextFormatter{
			FullTimestamp:   true,
			TimestampFormat: time.RFC3339,
		})
	}

	// Set output
	if err := logger.setOutput(); err != nil {
		return nil, fmt.Errorf("failed to set output: %w", err)
	}

	// Set default fields if any
	if len(config.Fields) > 0 {
		logger.logrus = logger.logrus.WithFields(config.Fields).Logger
	}

	// Initialize rotator if rotation is enabled
	if config.Rotation {
		logger.rotator = &LogRotator{
			config: config,
		}
	}

	return logger, nil
}

func (l *Logger) setOutput() error {
	l.mu.Lock()
	defer l.mu.Unlock()

	switch l.config.Output {
	case "stdout":
		l.logrus.SetOutput(os.Stdout)
	case "stderr":
		l.logrus.SetOutput(os.Stderr)
	default:
		// File output
		if l.file != nil {
			l.file.Close()
		}
		
		// Ensure directory exists
		dir := filepath.Dir(l.config.Output)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return fmt.Errorf("failed to create log directory: %w", err)
		}

		file, err := os.OpenFile(l.config.Output, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
		if err != nil {
			return fmt.Errorf("failed to open log file: %w", err)
		}
		l.file = file
		l.logrus.SetOutput(file)
	}

	return nil
}

func (l *Logger) logWithCaller(level LogLevel, message string, fields map[string]interface{}) {
	l.mu.RLock()
	defer l.mu.RUnlock()

	entry := l.logrus.WithFields(fields)
	
	// Add caller information
	if pc, file, line, ok := runtime.Caller(2); ok {
		fn := runtime.FuncForPC(pc)
		if fn != nil {
			entry = entry.WithFields(logrus.Fields{
				"source":   filepath.Base(file),
				"function": fn.Name(),
				"line":     line,
			})
		}
	}

	switch level {
	case DEBUG:
		entry.Debug(message)
	case INFO:
		entry.Info(message)
	case WARN:
		entry.Warn(message)
	case ERROR:
		entry.Error(message)
	case FATAL:
		entry.Fatal(message)
	}

	// Check rotation if enabled
	if l.rotator != nil && l.config.Rotation {
		l.rotator.checkRotation(l.config.Output)
	}
}

func (l *Logger) Debug(message string, fields ...map[string]interface{}) {
	allFields := l.mergeFields(fields...)
	l.logWithCaller(DEBUG, message, allFields)
}

func (l *Logger) Info(message string, fields ...map[string]interface{}) {
	allFields := l.mergeFields(fields...)
	l.logWithCaller(INFO, message, allFields)
}

func (l *Logger) Warn(message string, fields ...map[string]interface{}) {
	allFields := l.mergeFields(fields...)
	l.logWithCaller(WARN, message, allFields)
}

func (l *Logger) Error(message string, fields ...map[string]interface{}) {
	allFields := l.mergeFields(fields...)
	l.logWithCaller(ERROR, message, allFields)
}

func (l *Logger) Fatal(message string, fields ...map[string]interface{}) {
	allFields := l.mergeFields(fields...)
	l.logWithCaller(FATAL, message, allFields)
}

func (l *Logger) mergeFields(fields ...map[string]interface{}) map[string]interface{} {
	result := make(map[string]interface{})
	
	// Add default fields from config
	for k, v := range l.config.Fields {
		result[k] = v
	}
	
	// Add provided fields
	for _, fieldMap := range fields {
		for k, v := range fieldMap {
			result[k] = v
		}
	}
	
	return result
}

func (l *Logger) WithFields(fields map[string]interface{}) *Logger {
	newLogger := *l
	newConfig := l.config
	newConfig.Fields = l.mergeFields(fields)
	newLogger.config = newConfig
	
	// Recreate logger with new fields
	logger, _ := NewLogger(newConfig)
	return logger
}

func (l *Logger) SetLevel(level LogLevel) {
	l.mu.Lock()
	defer l.mu.Unlock()
	
	l.config.Level = level
	logrusLevel, _ := logrus.ParseLevel(string(level))
	l.logrus.SetLevel(logrusLevel)
}

func (l *Logger) GetLevel() LogLevel {
	l.mu.RLock()
	defer l.mu.RUnlock()
	return l.config.Level
}

func (l *Logger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()
	
	if l.file != nil {
		return l.file.Close()
	}
	return nil
}

func (lr *LogRotator) checkRotation(filePath string) {
	lr.mu.Lock()
	defer lr.mu.Unlock()

	// Get current file size
	info, err := os.Stat(filePath)
	if err != nil {
		return
	}

	// Convert max size from MB to bytes
	maxSizeBytes := lr.config.MaxSize * 1024 * 1024

	if info.Size() > maxSizeBytes {
		lr.rotateFile(filePath)
	}
}

func (lr *LogRotator) rotateFile(filePath string) {
	// Close current file
	// Rotate file by renaming with timestamp
	timestamp := time.Now().Format("20060102-150405")
	rotatedPath := fmt.Sprintf("%s.%s", filePath, timestamp)
	
	// Rename current file
	os.Rename(filePath, rotatedPath)
	
	// Compress if enabled
	if lr.config.Compress {
		go lr.compressFile(rotatedPath)
	}
	
	// Clean up old files if max files is set
	if lr.config.MaxFiles > 0 {
		lr.cleanupOldFiles(filePath)
	}
}

func (lr *LogRotator) compressFile(filePath string) {
	// This is a placeholder for compression logic
	// In a real implementation, you would use gzip compression
	// For simplicity, we'll just add a .compressed extension
	compressedPath := filePath + ".compressed"
	os.Rename(filePath, compressedPath)
}

func (lr *LogRotator) cleanupOldFiles(basePath string) {
	dir := filepath.Dir(basePath)
	baseName := filepath.Base(basePath)
	
	files, err := filepath.Glob(fmt.Sprintf("%s%s.*", dir, string(filepath.Separator), baseName))
	if err != nil {
		return
	}
	
	// Sort files by modification time and remove excess ones
	if len(files) > lr.config.MaxFiles {
		// Simple implementation - just remove the oldest files
		// In a real implementation, you'd sort by modification time
		for i := 0; i < len(files)-lr.config.MaxFiles; i++ {
			os.Remove(files[i])
		}
	}
}

func LoadLogConfig(configPath string) (LogConfig, error) {
	var config LogConfig
	
	data, err := os.ReadFile(configPath)
	if err != nil {
		return config, err
	}
	
	// Determine format by file extension
	ext := strings.ToLower(filepath.Ext(configPath))
	switch ext {
	case ".yaml", ".yml":
		err = yaml.Unmarshal(data, &config)
	case ".json":
		err = json.Unmarshal(data, &config)
	default:
		err = fmt.Errorf("unsupported config format: %s", ext)
	}
	
	return config, err
}

func (c LogConfig) Save(configPath string) error {
	var data []byte
	var err error
	
	// Determine format by file extension
	ext := strings.ToLower(filepath.Ext(configPath))
	switch ext {
	case ".yaml", ".yml":
		data, err = yaml.Marshal(c)
	case ".json":
		data, err = json.MarshalIndent(c, "", "  ")
	default:
		err = fmt.Errorf("unsupported config format: %s", ext)
	}
	
	if err != nil {
		return err
	}
	
	return os.WriteFile(configPath, data, 0644)
}

// Global logger instance
var defaultLogger *Logger
var defaultLoggerOnce sync.Once

func InitDefaultLogger(configPath string) error {
	var err error
	defaultLoggerOnce.Do(func() {
		config, loadErr := LoadLogConfig(configPath)
		if loadErr != nil {
			// Use default config
			config = LogConfig{
				Level:  INFO,
				Format: TEXT,
				Output: "stdout",
			}
		}
		defaultLogger, err = NewLogger(config)
	})
	return err
}

func GetDefaultLogger() *Logger {
	if defaultLogger == nil {
		// Initialize with default config
		defaultLogger, _ = NewLogger(LogConfig{
			Level:  INFO,
			Format: TEXT,
			Output: "stdout",
		})
	}
	return defaultLogger
}

func Debug(message string, fields ...map[string]interface{}) {
	GetDefaultLogger().Debug(message, fields...)
}

func Info(message string, fields ...map[string]interface{}) {
	GetDefaultLogger().Info(message, fields...)
}

func Warn(message string, fields ...map[string]interface{}) {
	GetDefaultLogger().Warn(message, fields...)
}

func Error(message string, fields ...map[string]interface{}) {
	GetDefaultLogger().Error(message, fields...)
}

func Fatal(message string, fields ...map[string]interface{}) {
	GetDefaultLogger().Fatal(message, fields...)
}
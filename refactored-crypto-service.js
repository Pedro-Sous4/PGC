const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');

// ================== Base Encryption Service ==================
class BaseEncryptionService {
  constructor(secretKey, encryptionAlgorithm = 'aes-256-cbc', keyDerivationAlgorithm = 'sha256') {
    if (!secretKey) {
      throw new Error('Secret key is required');
    }
    if (typeof secretKey !== 'string' || secretKey.length < 32) {
      throw new Error('Secret key must be a string of at least 32 characters');
    }
    this.secretKey = secretKey;
    this.algorithm = encryptionAlgorithm;
    this.keyDerivationAlgorithm = keyDerivationAlgorithm;
  }

  _deriveKey(salt, iterations = 100000) {
    return crypto.pbkdf2Sync(this.secretKey, salt, iterations, 32, this.keyDerivationAlgorithm);
  }

  _generateRandomBytes(size) {
    return crypto.randomBytes(size);
  }
}

// ================== Encryption Service ==================
class EncryptionService extends BaseEncryptionService {
  /**
   * Encrypts text content and returns an encrypted buffer
   * @param {string} text - The text content to encrypt
   * @returns {Buffer} Encrypted data as buffer
   */
  encryptText(text) {
    if (typeof text !== 'string') {
      throw new Error('Text must be a string');
    }

    try {
      const salt = this._generateRandomBytes(16);
      const iv = this._generateRandomBytes(16);
      const key = this._deriveKey(salt);
      
      const cipher = crypto.createCipher(this.algorithm, key);
      cipher.setAutoPadding(true);

      let encrypted = cipher.update(text, 'utf8', 'binary');
      encrypted += cipher.final('binary');

      // Combine salt + iv + encrypted data
      const encryptedBuffer = Buffer.concat([
        salt,
        iv,
        Buffer.from(encrypted, 'binary')
      ]);

      return encryptedBuffer;
    } catch (error) {
      throw new Error(`Encryption failed: ${error.message}`);
    }
  }

  /**
   * Encrypts the contents of a file and returns an encrypted buffer
   * @param {string} filePath - Path to the file to encrypt
   * @returns {Buffer} Encrypted file data as buffer
   */
  async encryptFile(filePath) {
    try {
      await fs.access(filePath);
    } catch (error) {
      throw new Error(`File not found: ${filePath}`);
    }

    const fileContent = await fs.readFile(filePath);
    return this.encryptBuffer(fileContent);
  }

  /**
   * Encrypts buffer data and returns an encrypted buffer
   * @param {Buffer} buffer - The buffer to encrypt
   * @returns {Buffer} Encrypted data as buffer
   */
  encryptBuffer(buffer) {
    if (!Buffer.isBuffer(buffer)) {
      throw new Error('Data must be a buffer');
    }

    try {
      const salt = this._generateRandomBytes(16);
      const iv = this._generateRandomBytes(16);
      const key = this._deriveKey(salt);
      
      const cipher = crypto.createCipher(this.algorithm, key);
      cipher.setAutoPadding(true);

      const encrypted = Buffer.concat([
        cipher.update(buffer),
        cipher.final()
      ]);

      // Combine salt + iv + encrypted data
      return Buffer.concat([
        salt,
        iv,
        encrypted
      ]);
    } catch (error) {
      throw new Error(`Encryption failed: ${error.message}`);
    }
  }

  /**
   * Encrypts the contents of a file and saves it to a new file
   * @param {string} inputFilePath - Path to the file to encrypt
   * @param {string} outputFilePath - Path where encrypted file will be saved
   */
  async encryptFileAndSave(inputFilePath, outputFilePath) {
    const encryptedData = await this.encryptFile(inputFilePath);
    await this._saveEncryptedFile(encryptedData, outputFilePath);
  }

  /**
   * Encrypts text and saves it to a file
   * @param {string} text - The text content to encrypt
   * @param {string} outputFilePath - Path where encrypted file will be saved
   */
  async encryptTextAndSave(text, outputFilePath) {
    const encryptedData = this.encryptText(text);
    await this._saveEncryptedFile(encryptedData, outputFilePath);
  }

  /**
   * Saves encrypted data to a file
   * @private
   */
  async _saveEncryptedFile(encryptedData, outputFilePath) {
    try {
      await fs.writeFile(outputFilePath, encryptedData);
      console.log(`File encrypted and saved to: ${outputFilePath}`);
    } catch (error) {
      throw new Error(`Failed to save encrypted file: ${error.message}`);
    }
  }
}

// ================== Decryption Service ==================
class DecryptionService extends BaseEncryptionService {
  /**
   * Decrypts an encrypted buffer and returns the original text
   * @param {Buffer} encryptedBuffer - The encrypted buffer
   * @returns {string} Decrypted text
   */
  decryptText(encryptedBuffer) {
    if (!Buffer.isBuffer(encryptedBuffer)) {
      throw new Error('Encrypted data must be a buffer');
    }

    try {
      // Extract salt, iv, and encrypted data
      const salt = encryptedBuffer.slice(0, 16);
      const iv = encryptedBuffer.slice(16, 32);
      const encryptedData = encryptedBuffer.slice(32);

      const key = this._deriveKey(salt);
      const decipher = crypto.createDecipher(this.algorithm, key);
      decipher.setAutoPadding(true);

      let decrypted = decipher.update(encryptedData, 'binary', 'utf8');
      decrypted += decipher.final('utf8');

      return decrypted;
    } catch (error) {
      throw new Error(`Decryption failed: ${error.message}`);
    }
  }

  /**
   * Decrypts an encrypted buffer and returns the original buffer
   * @param {Buffer} encryptedBuffer - The encrypted buffer
   * @returns {Buffer} Decrypted buffer
   */
  decryptBuffer(encryptedBuffer) {
    if (!Buffer.isBuffer(encryptedBuffer)) {
      throw new Error('Encrypted data must be a buffer');
    }

    try {
      // Extract salt, iv, and encrypted data
      const salt = encryptedBuffer.slice(0, 16);
      const iv = encryptedBuffer.slice(16, 32);
      const encryptedData = encryptedBuffer.slice(32);

      const key = this._deriveKey(salt);
      const decipher = crypto.createDecipher(this.algorithm, key);
      decipher.setAutoPadding(true);

      return Buffer.concat([
        decipher.update(encryptedData),
        decipher.final()
      ]);
    } catch (error) {
      throw new Error(`Decryption failed: ${error.message}`);
    }
  }

  /**
   * Decrypts a file and returns the decrypted content as buffer
   * @param {string} encryptedFilePath - Path to the encrypted file
   * @returns {Buffer} Decrypted file content as buffer
   */
  async decryptFile(encryptedFilePath) {
    try {
      await fs.access(encryptedFilePath);
    } catch (error) {
      throw new Error(`File not found: ${encryptedFilePath}`);
    }

    const encryptedData = await fs.readFile(encryptedFilePath);
    return this.decryptBuffer(encryptedData);
  }

  /**
   * Decrypts a file and saves it to a new file
   * @param {string} encryptedFilePath - Path to the encrypted file
   * @param {string} outputFilePath - Path where decrypted file will be saved
   */
  async decryptFileAndSave(encryptedFilePath, outputFilePath) {
    const decryptedData = await this.decryptFile(encryptedFilePath);
    await this._saveDecryptedFile(decryptedData, outputFilePath);
  }

  /**
   * Saves decrypted data to a file
   * @private
   */
  async _saveDecryptedFile(decryptedData, outputFilePath) {
    try {
      await fs.writeFile(outputFilePath, decryptedData);
      console.log(`File decrypted and saved to: ${outputFilePath}`);
    } catch (error) {
      throw new Error(`Failed to save decrypted file: ${error.message}`);
    }
  }
}

// ================== Unified Crypto Service ==================
class CryptoService {
  constructor(secretKey, encryptionAlgorithm = 'aes-256-cbc', keyDerivationAlgorithm = 'sha256') {
    this.encryptionService = new EncryptionService(secretKey, encryptionAlgorithm, keyDerivationAlgorithm);
    this.decryptionService = new DecryptionService(secretKey, encryptionAlgorithm, keyDerivationAlgorithm);
  }

  // Encryption methods - delegate to encryption service
  encryptText(text) {
    return this.encryptionService.encryptText(text);
  }

  encryptBuffer(buffer) {
    return this.encryptionService.encryptBuffer(buffer);
  }

  async encryptFile(filePath) {
    return this.encryptionService.encryptFile(filePath);
  }

  async encryptFileAndSave(inputFilePath, outputFilePath) {
    return this.encryptionService.encryptFileAndSave(inputFilePath, outputFilePath);
  }

  async encryptTextAndSave(text, outputFilePath) {
    return this.encryptionService.encryptTextAndSave(text, outputFilePath);
  }

  // Decryption methods - delegate to decryption service
  decryptText(encryptedBuffer) {
    return this.decryptionService.decryptText(encryptedBuffer);
  }

  decryptBuffer(encryptedBuffer) {
    return this.decryptionService.decryptBuffer(encryptedBuffer);
  }

  async decryptFile(encryptedFilePath) {
    return this.decryptionService.decryptFile(encryptedFilePath);
  }

  async decryptFileAndSave(encryptedFilePath, outputFilePath) {
    return this.decryptionService.decryptFileAndSave(encryptedFilePath, outputFilePath);
  }
}

// ================== Usage Examples ==================
async function demonstrateUsage() {
  const SECRET_KEY = 'my-super-secret-key-of-exactly-32-bytes!!';
  
  // Example 1: Using the unified CryptoService (recommended)
  console.log('=== Using CryptoService (Unified Interface) ===');
  const cryptoService = new CryptoService(SECRET_KEY);

  // Encrypt and decrypt text
  const originalText = 'This is a secret message that needs to be encrypted!';
  const encryptedBuffer = cryptoService.encryptText(originalText);
  const decryptedText = cryptoService.decryptText(encryptedBuffer);
  console.log('Original:', originalText);
  console.log('Decrypted:', decryptedText);
  console.log('Encryption successful:', originalText === decryptedText);

  // Example 2: Using separate services (for advanced use cases)
  console.log('\n=== Using Separate Encryption and Decryption Services ===');
  const encryptService = new EncryptionService(SECRET_KEY);
  const decryptService = new DecryptionService(SECRET_KEY);

  // Encrypt and decrypt buffer
  const originalBuffer = Buffer.from('Binary data to encrypt', 'utf8');
  const encryptedData = encryptService.encryptBuffer(originalBuffer);
  const decryptedBuffer = decryptService.decryptBuffer(encryptedData);
  console.log('Original buffer:', originalBuffer.toString());
  console.log('Decrypted buffer:', decryptedBuffer.toString());
  console.log('Buffer encryption successful:', originalBuffer.equals(decryptedBuffer));

  // Example 3: File operations
  console.log('\n=== File Operations ===');
  const testFilePath = path.join(__dirname, 'test.txt');
  const encryptedFilePath = path.join(__dirname, 'test.txt.enc');
  const decryptedFilePath = path.join(__dirname, 'test-decrypted.txt');

  // Create a test file
  await fs.writeFile(testFilePath, 'This is the content of the test file.');
  
  // Encrypt file and save
  await cryptoService.encryptFileAndSave(testFilePath, encryptedFilePath);
  
  // Decrypt file and save
  await cryptoService.decryptFileAndSave(encryptedFilePath, decryptedFilePath);

  // Verify the decrypted content
  const originalContent = await fs.readFile(testFilePath, 'utf8');
  const decryptedContent = await fs.readFile(decryptedFilePath, 'utf8');
  console.log('Original file content:', originalContent);
  console.log('Decrypted file content:', decryptedContent);
  console.log('File encryption successful:', originalContent === decryptedContent);

  // Cleanup test files
  await fs.unlink(testFilePath).catch(() => {});
  await fs.unlink(encryptedFilePath).catch(() => {});
  await fs.unlink(decryptedFilePath).catch(() => {});
}

// Export classes for use in other modules
module.exports = {
  BaseEncryptionService,
  EncryptionService,
  DecryptionService,
  CryptoService
};

// Run demonstration if this file is executed directly
if (require.main === module) {
  demonstrateUsage().catch(console.error);
}
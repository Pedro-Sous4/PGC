import { Injectable } from '@angular/core';
import { BaseDataConverter, DataConversionError, validateRequired, validateType } from '../core/data-converter';
import { UserDTO, ProductDTO, AddressDTO } from '../models/dtos';
import { User, Product, Address } from '../models/domain';

@Injectable({
  providedIn: 'root'
})
export class UserDataConverter extends BaseDataConverter<UserDTO, User> {
  
  toDomain(dto: UserDTO): User {
    try {
      const id = validateRequired(dto.id, 'id');
      const firstName = validateRequired(dto.firstName, 'firstName');
      const lastName = validateRequired(dto.lastName, 'lastName');
      const email = validateRequired(dto.email, 'email');
      
      validateType(id, 'number', 'id');
      validateType(firstName, 'string', 'firstName');
      validateType(lastName, 'string', 'lastName');
      validateType(email, 'string', 'email');

      if (!this.isValidEmail(email)) {
        throw new DataConversionError(`Invalid email format: ${email}`, email);
      }

      const dateOfBirth = this.parseDate(dto.dateOfBirth, 'dateOfBirth');
      const isActive = dto.isActive !== undefined ? this.safeBooleanConversion(dto.isActive) : true;
      const createdAt = this.parseDate(dto.createdAt, 'createdAt', true);
      const lastLoginAt = dto.lastLoginAt ? this.parseDate(dto.lastLoginAt, 'lastLoginAt') : null;

      return new User(
        id,
        firstName,
        lastName,
        email,
        dateOfBirth,
        isActive,
        createdAt,
        lastLoginAt
      );
    } catch (error) {
      if (error instanceof DataConversionError) {
        throw error;
      }
      throw new DataConversionError(`Failed to convert UserDTO to User: ${error.message}`, dto);
    }
  }

  toDTO(domain: User): UserDTO {
    return {
      id: domain.id,
      firstName: domain.firstName,
      lastName: domain.lastName,
      email: domain.email,
      dateOfBirth: this.formatDate(domain.dateOfBirth),
      isActive: domain.isActive,
      createdAt: this.formatDate(domain.createdAt),
      lastLoginAt: domain.lastLoginAt ? this.formatDate(domain.lastLoginAt) : undefined
    };
  }

  private isValidEmail(email: string): boolean {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  private parseDate(dateString: string | undefined, fieldName: string, allowDefault: boolean = false): Date {
    if (!dateString) {
      if (allowDefault) {
        return new Date();
      }
      throw new DataConversionError(`Field '${fieldName}' is required`, dateString);
    }

    const date = new Date(dateString);
    if (!this.isValidDate(date)) {
      throw new DataConversionError(`Invalid date format for '${fieldName}': ${dateString}`, dateString);
    }

    return date;
  }

  private formatDate(date: Date): string {
    return date.toISOString();
  }
}
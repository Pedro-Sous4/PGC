export interface DataConverter<DTO, Domain> {
  toDomain(dto: DTO): Domain;
  toDTO(domain: Domain): DTO;
  toDomainArray(dtos: DTO[]): Domain[];
  toDTOArray(domains: Domain[]): DTO[];
}

export abstract class BaseDataConverter<DTO, Domain> implements DataConverter<DTO, Domain> {
  abstract toDomain(dto: DTO): Domain;
  abstract toDTO(domain: Domain): DTO;

  toDomainArray(dtos: DTO[]): Domain[] {
    return dtos.map(dto => this.toDomain(dto));
  }

  toDTOArray(domains: Domain[]): DTO[] {
    return domains.map(domain => this.toDTO(domain));
  }

  protected isValidDate(date: any): date is Date {
    return date instanceof Date && !isNaN(date.getTime());
  }

  protected safeStringConversion(value: any): string {
    if (value === null || value === undefined) {
      return '';
    }
    return String(value);
  }

  protected safeNumberConversion(value: any): number {
    if (value === null || value === undefined || value === '') {
      return 0;
    }
    const num = Number(value);
    return isNaN(num) ? 0 : num;
  }

  protected safeBooleanConversion(value: any): boolean {
    if (value === null || value === undefined) {
      return false;
    }
    if (typeof value === 'boolean') {
      return value;
    }
    if (typeof value === 'string') {
      return value.toLowerCase() === 'true';
    }
    return Boolean(value);
  }
}

export class DataConversionError extends Error {
  constructor(message: string, public readonly source?: any) {
    super(message);
    this.name = 'DataConversionError';
  }
}

export function validateRequired<T>(value: T, fieldName: string): T {
  if (value === null || value === undefined) {
    throw new DataConversionError(`Required field '${fieldName}' is missing or null`, value);
  }
  return value;
}

export function validateType<T>(value: any, expectedType: string, fieldName: string): T {
  if (value === null || value === undefined) {
    throw new DataConversionError(`Field '${fieldName}' is null or undefined`, value);
  }
  
  if (typeof value !== expectedType) {
    throw new DataConversionError(
      `Field '${fieldName}' must be of type ${expectedType}, got ${typeof value}`,
      value
    );
  }
  
  return value as T;
}
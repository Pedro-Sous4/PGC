import { Injectable } from '@angular/core';
import { BaseDataConverter, DataConversionError, validateRequired, validateType } from '../core/data-converter';
import { ProductDTO } from '../models/dtos';
import { Product } from '../models/domain';

@Injectable({
  providedIn: 'root'
})
export class ProductDataConverter extends BaseDataConverter<ProductDTO, Product> {
  
  toDomain(dto: ProductDTO): Product {
    try {
      const id = validateRequired(dto.id, 'id');
      const name = validateRequired(dto.name, 'name');
      const description = dto.description || '';
      const price = dto.price !== undefined ? dto.price : 0;
      const category = dto.category || 'uncategorized';
      const inStock = dto.inStock !== undefined ? this.safeBooleanConversion(dto.inStock) : true;
      const sku = validateRequired(dto.sku, 'sku');
      
      validateType(id, 'number', 'id');
      validateType(name, 'string', 'name');
      validateType(description, 'string', 'description');
      validateType(price, 'number', 'price');
      validateType(category, 'string', 'category');
      validateType(sku, 'string', 'sku');

      if (price < 0) {
        throw new DataConversionError(`Product price cannot be negative: ${price}`, price);
      }

      if (name.trim().length === 0) {
        throw new DataConversionError('Product name cannot be empty', name);
      }

      if (sku.trim().length === 0) {
        throw new DataConversionError('Product SKU cannot be empty', sku);
      }

      const createdAt = dto.createdAt ? new Date(dto.createdAt) : new Date();
      const updatedAt = dto.updatedAt ? new Date(dto.updatedAt) : createdAt;

      if (!this.isValidDate(createdAt)) {
        throw new DataConversionError(`Invalid createdAt date: ${dto.createdAt}`, dto.createdAt);
      }

      if (!this.isValidDate(updatedAt)) {
        throw new DataConversionError(`Invalid updatedAt date: ${dto.updatedAt}`, dto.updatedAt);
      }

      return new Product(
        id,
        this.safeStringConversion(name),
        this.safeStringConversion(description),
        this.safeNumberConversion(price),
        this.safeStringConversion(category),
        inStock,
        this.safeStringConversion(sku),
        createdAt,
        updatedAt
      );
    } catch (error) {
      if (error instanceof DataConversionError) {
        throw error;
      }
      throw new DataConversionError(`Failed to convert ProductDTO to Product: ${error.message}`, dto);
    }
  }

  toDTO(domain: Product): ProductDTO {
    return {
      id: domain.id,
      name: domain.name,
      description: domain.description,
      price: domain.price,
      category: domain.category,
      inStock: domain.inStock,
      sku: domain.sku,
      createdAt: domain.createdAt.toISOString(),
      updatedAt: domain.updatedAt.toISOString()
    };
  }
}
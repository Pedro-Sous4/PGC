export interface UserDTO {
  id?: number;
  firstName?: string;
  lastName?: string;
  email?: string;
  dateOfBirth?: string;
  isActive?: boolean;
  createdAt?: string;
  lastLoginAt?: string;
}

export interface ProductDTO {
  id?: number;
  name?: string;
  description?: string;
  price?: number;
  category?: string;
  inStock?: boolean;
  sku?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AddressDTO {
  id?: number;
  street?: string;
  city?: string;
  state?: string;
  zipCode?: string;
  country?: string;
  isPrimary?: boolean;
}
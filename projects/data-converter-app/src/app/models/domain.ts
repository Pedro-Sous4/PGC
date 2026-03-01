export class User {
  constructor(
    public readonly id: number,
    public readonly firstName: string,
    public readonly lastName: string,
    public readonly email: string,
    public readonly dateOfBirth: Date,
    public readonly isActive: boolean,
    public readonly createdAt: Date,
    public readonly lastLoginAt: Date | null = null
  ) {}

  get fullName(): string {
    return `${this.firstName} ${this.lastName}`;
  }

  get age(): number {
    const today = new Date();
    const birthDate = new Date(this.dateOfBirth);
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDiff = today.getMonth() - birthDate.getMonth();
    
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
      age--;
    }
    
    return age;
  }

  get domainKey(): string {
    return `user_${this.id}`;
  }

  equals(other: User): boolean {
    return this.id === other.id;
  }
}

export class Product {
  constructor(
    public readonly id: number,
    public readonly name: string,
    public readonly description: string,
    public readonly price: number,
    public readonly category: string,
    public readonly inStock: boolean,
    public readonly sku: string,
    public readonly createdAt: Date,
    public readonly updatedAt: Date
  ) {}

  get formattedPrice(): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(this.price);
  }

  get isAvailable(): boolean {
    return this.inStock && this.price > 0;
  }

  get domainKey(): string {
    return `product_${this.sku}`;
  }

  equals(other: Product): boolean {
    return this.id === other.id;
  }
}

export class Address {
  constructor(
    public readonly id: number,
    public readonly street: string,
    public readonly city: string,
    public readonly state: string,
    public readonly zipCode: string,
    public readonly country: string,
    public readonly isPrimary: boolean
  ) {}

  get fullAddress(): string {
    return `${this.street}, ${this.city}, ${this.state} ${this.zipCode}, ${this.country}`;
  }

  get shortAddress(): string {
    return `${this.city}, ${this.state}`;
  }

  get domainKey(): string {
    return `address_${this.id}`;
  }

  equals(other: Address): boolean {
    return this.id === other.id;
  }
}
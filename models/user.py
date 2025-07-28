from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr, field_validator
from passlib.context import CryptContext
from bson import ObjectId
import secrets


class PyObjectId(ObjectId):
    """Custom ObjectId for MongoDB integration with Pydantic."""
    
    @classmethod
    def __get_pydantic_json_schema__(cls, _source_type, _handler):
        return {"type": "string"}
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserPreferences(BaseModel):
    """User preferences and settings."""
    
    # Notification preferences
    email_notifications: bool = Field(True, description="Enable email notifications")
    price_alerts: bool = Field(True, description="Enable price drop alerts")
    new_listings: bool = Field(False, description="Notify about new matching listings")
    weekly_digest: bool = Field(True, description="Weekly summary email")
    
    # Search preferences
    default_search_radius: int = Field(10, description="Default search radius in km")
    preferred_property_types: List[str] = Field(default_factory=list, description="Preferred property types")
    preferred_listing_types: List[str] = Field(default_factory=list, description="Preferred listing types (sell/rent)")
    max_price_range: Optional[int] = Field(None, description="Maximum price range")
    min_area: Optional[float] = Field(None, description="Minimum area in sqm")
    
    # UI preferences
    default_view: str = Field("grid", description="Default listings view (grid/list/map)")
    listings_per_page: int = Field(20, description="Listings per page")
    language: str = Field("en", description="Preferred language")
    currency: str = Field("EUR", description="Preferred currency")


class UserStats(BaseModel):
    """User engagement statistics."""
    
    total_saved_listings: int = Field(0, description="Total saved listings")
    total_searches: int = Field(0, description="Total searches performed")
    total_views: int = Field(0, description="Total listing views")
    total_contacts: int = Field(0, description="Total contact forms submitted")
    total_comparisons: int = Field(0, description="Total property comparisons")
    total_shares: int = Field(0, description="Total property shares")
    account_created: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    engagement_score: float = Field(0.0, description="Calculated engagement score")


class UserBase(BaseModel):
    """Base user model."""
    
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    phone: Optional[str] = Field(None, description="Phone number")
    
    # Profile information
    profile_picture: Optional[str] = Field(None, description="Profile picture URL")
    bio: Optional[str] = Field(None, max_length=500, description="User bio")
    
    # Account status
    is_active: bool = Field(True, description="Account is active")
    is_verified: bool = Field(False, description="Email is verified")
    is_premium: bool = Field(False, description="Premium subscription status")
    
    # Preferences and stats
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    stats: UserStats = Field(default_factory=UserStats)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(None)
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Validate email format."""
        return v.lower().strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v):
        """Validate phone number format."""
        if v is None:
            return v
        # Basic phone validation - can be enhanced
        phone_clean = ''.join(filter(str.isdigit, v))
        if len(phone_clean) < 8:
            raise ValueError('Phone number must be at least 8 digits')
        return v
    
    @property
    def full_name(self) -> str:
        """Get full name."""
        return f"{self.first_name} {self.last_name}"


class User(UserBase):
    """Full user model with password and MongoDB ObjectId."""
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    password_hash: str = Field(..., description="Hashed password")
    email_verification_token: Optional[str] = Field(None)
    password_reset_token: Optional[str] = Field(None)
    password_reset_expires: Optional[datetime] = Field(None)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
    
    @classmethod
    def create_password_hash(cls, password: str) -> str:
        """Create password hash."""
        return pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify password."""
        return pwd_context.verify(password, self.password_hash)
    
    def generate_verification_token(self) -> str:
        """Generate email verification token."""
        token = secrets.token_urlsafe(32)
        self.email_verification_token = token
        return token
    
    def generate_password_reset_token(self) -> str:
        """Generate password reset token."""
        token = secrets.token_urlsafe(32)
        self.password_reset_token = token
        self.password_reset_expires = datetime.utcnow().replace(hour=datetime.utcnow().hour + 1)  # 1 hour expiry
        return token
    
    def update_last_activity(self):
        """Update last activity timestamp."""
        self.stats.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def increment_engagement(self, action: str, value: int = 1):
        """Increment engagement metrics."""
        if action == 'search':
            self.stats.total_searches += value
        elif action == 'view':
            self.stats.total_views += value
        elif action == 'save':
            self.stats.total_saved_listings += value
        elif action == 'contact':
            self.stats.total_contacts += value
        elif action == 'comparison':
            self.stats.total_comparisons += value
        elif action == 'share':
            self.stats.total_shares += value
        
        # Recalculate engagement score
        self.calculate_engagement_score()
        self.update_last_activity()
    
    def calculate_engagement_score(self):
        """Calculate user engagement score based on activities."""
        # Weighted scoring system
        score = (
            self.stats.total_saved_listings * 5 +
            self.stats.total_searches * 1 +
            self.stats.total_views * 2 +
            self.stats.total_contacts * 10 +
            self.stats.total_comparisons * 3 +
            self.stats.total_shares * 4
        )
        
        # Account age bonus (max 50 points)
        days_since_creation = (datetime.utcnow() - self.stats.account_created).days
        age_bonus = min(days_since_creation * 0.5, 50)
        
        # Activity recency bonus (max 25 points)
        days_since_activity = (datetime.utcnow() - self.stats.last_activity).days
        recency_bonus = max(25 - days_since_activity, 0) if days_since_activity <= 30 else 0
        
        self.stats.engagement_score = score + age_bonus + recency_bonus


class UserCreate(UserBase):
    """Model for creating new users."""
    
    password: str = Field(..., min_length=8, description="User password")
    confirm_password: str = Field(..., description="Password confirmation")
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Validate password confirmation."""
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('Passwords do not match')
        return v
    
    def to_user(self) -> User:
        """Convert to User model with hashed password."""
        user_data = self.model_dump(exclude={'password', 'confirm_password'})
        return User(
            **user_data,
            password_hash=User.create_password_hash(self.password),
            email_verification_token=secrets.token_urlsafe(32)
        )


class UserUpdate(BaseModel):
    """Model for updating user information."""
    
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    preferences: Optional[UserPreferences] = None
    
    class Config:
        arbitrary_types_allowed = True


class UserResponse(UserBase):
    """Model for API responses (excludes sensitive data)."""
    
    id: str
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True


class UserLogin(BaseModel):
    """Model for user login."""
    
    email: EmailStr
    password: str
    remember_me: bool = Field(False, description="Remember login session")


class PasswordChange(BaseModel):
    """Model for password change."""
    
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str
    
    @field_validator('confirm_new_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Validate new password confirmation."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('New passwords do not match')
        return v


class PasswordReset(BaseModel):
    """Model for password reset."""
    
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Model for password reset confirmation."""
    
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        """Validate password confirmation."""
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class EmailVerification(BaseModel):
    """Model for email verification."""
    
    token: str


class UserActivity(BaseModel):
    """Model for tracking user activities."""
    
    user_id: str
    activity_type: str = Field(..., description="Type of activity (search, view, save, etc.)")
    resource_type: str = Field(..., description="Type of resource (listing, search, etc.)")
    resource_id: Optional[str] = Field(None, description="ID of the resource")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional activity data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = Field(None)
    user_agent: Optional[str] = Field(None)
    
    class Config:
        arbitrary_types_allowed = True
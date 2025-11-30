"""Data storage backends for financial filing data.

Provides abstraction layer for storing scraped filing results and content
to various storage backends including local disk and cloud storage.
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from scraper import FilingResult, FilingFormat


class DataStore(ABC):
    """Abstract base class for data storage backends."""
    
    @abstractmethod
    def store_filing_metadata(self, filings: List[FilingResult]) -> bool:
        """Store filing metadata to the backend.
        
        Args:
            filings: List of FilingResult objects to store
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageException: If storage operation fails
        """
        pass
    
    @abstractmethod
    def store_filing_content(self, filing: FilingResult, content: bytes) -> bool:
        """Store filing content to the backend.
        
        Args:
            filing: FilingResult object
            content: Raw filing content as bytes
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            StorageException: If storage operation fails
        """
        pass
    
    @abstractmethod
    def get_filing_content(self, filing: FilingResult) -> Optional[bytes]:
        """Retrieve filing content from the backend.
        
        Args:
            filing: FilingResult object to retrieve
            
        Returns:
            Raw filing content as bytes, or None if not found
            
        Raises:
            StorageException: If retrieval operation fails
        """
        pass
    
    @abstractmethod
    def list_stored_filings(self) -> List[FilingResult]:
        """List all stored filing metadata.
        
        Returns:
            List of FilingResult objects
            
        Raises:
            StorageException: If listing operation fails
        """
        pass
    
    @abstractmethod
    def exists(self, filing: FilingResult) -> bool:
        """Check if filing content exists in storage.
        
        Args:
            filing: FilingResult object to check
            
        Returns:
            True if filing content exists, False otherwise
        """
        pass


class StorageException(Exception):
    """Exception raised for storage operation failures."""
    pass


class LocalDiskStore(DataStore):
    """Local disk storage backend for filing data."""
    
    def __init__(self, base_path: Union[str, Path] = "./data"):
        """Initialize local disk storage.
        
        Args:
            base_path: Base directory for storing files
        """
        self.base_path = Path(base_path)
        self.metadata_file = self.base_path / "filings_metadata.json"
        self.content_dir = self.base_path / "content"
        
        # Create directory structure
        self._setup_directories()
        
        # Load existing metadata
        self._metadata_cache = self._load_metadata()
    
    def _setup_directories(self) -> None:
        """Create necessary directory structure."""
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            self.content_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Storage directories created at {self.base_path}")
        except OSError as e:
            raise StorageException(f"Failed to create storage directories: {e}")
    
    def _load_metadata(self) -> Dict[str, dict]:
        """Load filing metadata from JSON file.
        
        Returns:
            Dictionary mapping filing URLs to metadata
        """
        if not self.metadata_file.exists():
            return {}
            
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logging.info(f"Loaded {len(data)} filing records from metadata file")
                return data
        except (json.JSONDecodeError, OSError) as e:
            logging.warning(f"Failed to load metadata file: {e}")
            return {}
    
    def _save_metadata(self) -> None:
        """Save metadata cache to JSON file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata_cache, f, indent=2, default=str)
                logging.debug(f"Saved {len(self._metadata_cache)} filing records to metadata file")
        except OSError as e:
            raise StorageException(f"Failed to save metadata file: {e}")
    
    def _get_filing_filename(self, filing: FilingResult) -> str:
        """Generate filename for filing content.
        
        Args:
            filing: FilingResult object
            
        Returns:
            Sanitized filename for the filing
        """
        # Create safe filename from filing data
        date_str = filing.filing_date.strftime("%Y-%m-%d")
        safe_name = f"{filing.last_name}_{filing.first_name}_{date_str}"
        
        # Remove unsafe characters
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in ('_', '-'))
        
        # Add appropriate extension
        extension = ".html" if filing.filing_format == FilingFormat.HTML else ".pdf"
        
        # Extract filing ID from URL for uniqueness
        filing_id = filing.filing_url.split('/')[-2] if '/' in filing.filing_url else "unknown"
        
        return f"{safe_name}_{filing_id}{extension}"
    
    def _filing_to_dict(self, filing: FilingResult) -> dict:
        """Convert FilingResult to dictionary for JSON serialization.
        
        Args:
            filing: FilingResult object
            
        Returns:
            Dictionary representation of filing
        """
        return {
            'first_name': filing.first_name,
            'last_name': filing.last_name,
            'office_name': filing.office_name,
            'filing_date': filing.filing_date.isoformat(),
            'filing_type': filing.filing_type.value,
            'filing_url': filing.filing_url,
            'filing_format': filing.filing_format.value,
            'stored_at': datetime.now().isoformat(),
            'content_filename': self._get_filing_filename(filing)
        }
    
    def _dict_to_filing(self, data: dict) -> FilingResult:
        """Convert dictionary back to FilingResult object.
        
        Args:
            data: Dictionary representation of filing
            
        Returns:
            FilingResult object
        """
        from constants import FilingType
        
        return FilingResult(
            first_name=data['first_name'],
            last_name=data['last_name'],
            office_name=data['office_name'],
            filing_date=datetime.fromisoformat(data['filing_date']),
            filing_type=FilingType(data['filing_type']),
            filing_url=data['filing_url'],
            filing_format=FilingFormat(data['filing_format'])
        )
    
    def store_filing_metadata(self, filings: List[FilingResult]) -> bool:
        """Store filing metadata to local JSON file.
        
        Args:
            filings: List of FilingResult objects to store
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If storage operation fails
        """
        try:
            for filing in filings:
                filing_dict = self._filing_to_dict(filing)
                self._metadata_cache[filing.filing_url] = filing_dict
            
            self._save_metadata()
            logging.info(f"Stored metadata for {len(filings)} filings")
            return True
            
        except Exception as e:
            raise StorageException(f"Failed to store filing metadata: {e}")
    
    def store_filing_content(self, filing: FilingResult, content: bytes) -> bool:
        """Store filing content to local disk.
        
        Args:
            filing: FilingResult object
            content: Raw filing content as bytes
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If storage operation fails
        """
        try:
            filename = self._get_filing_filename(filing)
            file_path = self.content_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(content)
            
            # Update metadata cache with content info
            if filing.filing_url in self._metadata_cache:
                self._metadata_cache[filing.filing_url]['content_size'] = len(content)
                self._metadata_cache[filing.filing_url]['content_stored_at'] = datetime.now().isoformat()
                self._save_metadata()
            
            logging.info(f"Stored content for filing {filename} ({len(content)} bytes)")
            return True
            
        except OSError as e:
            raise StorageException(f"Failed to store filing content: {e}")
    
    def get_filing_content(self, filing: FilingResult) -> Optional[bytes]:
        """Retrieve filing content from local disk.
        
        Args:
            filing: FilingResult object to retrieve
            
        Returns:
            Raw filing content as bytes, or None if not found
        """
        try:
            filename = self._get_filing_filename(filing)
            file_path = self.content_dir / filename
            
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logging.debug(f"Retrieved content for filing {filename} ({len(content)} bytes)")
            return content
            
        except OSError as e:
            logging.error(f"Failed to retrieve filing content: {e}")
            return None
    
    def list_stored_filings(self) -> List[FilingResult]:
        """List all stored filing metadata.
        
        Returns:
            List of FilingResult objects
        """
        try:
            filings = []
            for filing_data in self._metadata_cache.values():
                filing = self._dict_to_filing(filing_data)
                filings.append(filing)
            
            logging.debug(f"Listed {len(filings)} stored filings")
            return filings
            
        except Exception as e:
            raise StorageException(f"Failed to list stored filings: {e}")
    
    def exists(self, filing: FilingResult) -> bool:
        """Check if filing content exists in local storage.
        
        Args:
            filing: FilingResult object to check
            
        Returns:
            True if filing content exists, False otherwise
        """
        filename = self._get_filing_filename(filing)
        file_path = self.content_dir / filename
        return file_path.exists()
    
    def get_storage_stats(self) -> Dict[str, Union[int, str]]:
        """Get storage statistics.
        
        Returns:
            Dictionary with storage statistics
        """
        total_files = len(list(self.content_dir.glob('*')))
        total_size = sum(f.stat().st_size for f in self.content_dir.glob('*'))
        
        return {
            'total_filings': len(self._metadata_cache),
            'total_content_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'base_path': str(self.base_path),
            'content_directory': str(self.content_dir),
            'metadata_file': str(self.metadata_file)
        }


def main():
    """Example usage of the LocalDiskStore."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize local disk store
    store = LocalDiskStore("./filing_data")
    
    # Print storage statistics
    stats = store.get_storage_stats()
    print("Storage Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # List existing filings
    existing_filings = store.list_stored_filings()
    print(f"\nFound {len(existing_filings)} existing filings in storage")
    
    for filing in existing_filings[:5]:  # Show first 5
        content_exists = store.exists(filing)
        print(f"  {filing.last_name}, {filing.first_name} - {filing.filing_date.date()} - Content: {'Yes' if content_exists else 'No'}")


if __name__ == "__main__":
    main()
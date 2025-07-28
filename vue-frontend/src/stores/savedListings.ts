import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ListingResponse } from '@/services/api'

export const useSavedListingsStore = defineStore('savedListings', () => {
  // State
  const savedListings = ref<ListingResponse[]>([])
  const storageKey = 'proscrape-saved-listings'

  // Getters
  const count = computed(() => savedListings.value.length)
  const isEmpty = computed(() => savedListings.value.length === 0)
  const listingIds = computed(() => savedListings.value.map(listing => listing.id))

  // Actions
  const loadFromStorage = () => {
    try {
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        savedListings.value = JSON.parse(stored)
      }
    } catch (error) {
      console.error('Error loading saved listings from storage:', error)
      savedListings.value = []
    }
  }

  const saveToStorage = () => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(savedListings.value))
    } catch (error) {
      console.error('Error saving listings to storage:', error)
    }
  }

  const addToSaved = (listing: ListingResponse) => {
    const exists = savedListings.value.find(item => item.id === listing.id)
    if (!exists) {
      savedListings.value.unshift(listing) // Add to beginning
      saveToStorage()
    }
  }

  const removeFromSaved = (listingId: string) => {
    const index = savedListings.value.findIndex(item => item.id === listingId)
    if (index > -1) {
      savedListings.value.splice(index, 1)
      saveToStorage()
    }
  }

  const isListingSaved = (listingId: string): boolean => {
    return listingIds.value.includes(listingId)
  }

  const clearAll = () => {
    savedListings.value = []
    saveToStorage()
  }

  const updateListing = (updatedListing: ListingResponse) => {
    const index = savedListings.value.findIndex(item => item.id === updatedListing.id)
    if (index > -1) {
      savedListings.value[index] = updatedListing
      saveToStorage()
    }
  }

  // Initialize store
  const initialize = () => {
    loadFromStorage()
  }

  return {
    // State
    savedListings,
    
    // Getters
    count,
    isEmpty,
    listingIds,
    
    // Actions
    addToSaved,
    removeFromSaved,
    isListingSaved,
    clearAll,
    updateListing,
    initialize,
  }
})

export type SavedListingsStore = ReturnType<typeof useSavedListingsStore>
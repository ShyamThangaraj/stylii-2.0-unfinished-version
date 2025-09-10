import { create } from "zustand"
import type { DesignResult } from "./client"

interface StyliiStore {
  // Form state
  images: File[]
  budget: number
  style: string
  notes: string
  selectedProducts: string[]

  // UI state
  isGenerating: boolean
  error: string | null

  // Results
  results: DesignResult[]
  currentResultId: string | null
  recommendedProducts: any[]
  amazonSearchQueries: string[]
  compositeImageUrl?: string
  
  // Cache for products by style
  productsCache: Record<string, { products: any[], queries: string[], timestamp: number }>

  // Actions
  setImages: (images: File[]) => void
  setBudget: (budget: number) => void
  setStyle: (style: string) => void
  setNotes: (notes: string) => void
  setSelectedProducts: (products: string[]) => void
  setIsGenerating: (isGenerating: boolean) => void
  setError: (error: string | null) => void
  addResult: (result: DesignResult) => void
  setCurrentResult: (id: string) => void
  setRecommendedProducts: (products: any[]) => void
  setAmazonSearchQueries: (queries: string[]) => void
  setCompositeImageUrl: (url?: string) => void
  setProductsCache: (style: string, products: any[], queries: string[]) => void
  getProductsFromCache: (style: string) => { products: any[], queries: string[] } | null
  reset: () => void
}

export const useStyliiStore = create<StyliiStore>((set) => ({
  // Initial state
  images: [],
  budget: 5000,
  style: "",
  notes: "",
  selectedProducts: [],
  isGenerating: false,
  error: null,
  results: [],
  currentResultId: null,
  recommendedProducts: [],
  amazonSearchQueries: [],
  compositeImageUrl: undefined,
  productsCache: {},

  // Actions
  setImages: (images) => set({ images }),
  setBudget: (budget) => set({ budget }),
  setStyle: (style) => set({ style }),
  setNotes: (notes) => set({ notes }),
  setSelectedProducts: (selectedProducts) => set({ selectedProducts }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),
  addResult: (result) =>
    set((state) => ({
      results: [result, ...state.results],
      currentResultId: result.id,
    })),
  setCurrentResult: (id) => set({ currentResultId: id }),
  setRecommendedProducts: (recommendedProducts) => set({ recommendedProducts }),
  setAmazonSearchQueries: (amazonSearchQueries) => set({ amazonSearchQueries }),
  setCompositeImageUrl: (compositeImageUrl) => set({ compositeImageUrl }),
  setProductsCache: (style, products, queries) => 
    set((state) => ({
      productsCache: {
        ...state.productsCache,
        [style]: {
          products,
          queries,
          timestamp: Date.now()
        }
      }
    })),
  getProductsFromCache: (style) => {
    const state = useStyliiStore.getState()
    const cached = state.productsCache[style]
    if (cached) {
      // Cache is valid for 1 hour (3600000 ms)
      const isExpired = Date.now() - cached.timestamp > 3600000
      if (!isExpired) {
        return { products: cached.products, queries: cached.queries }
      }
    }
    return null
  },
  reset: () =>
    set({
      images: [],
      budget: 5000,
      style: "",
      notes: "",
      selectedProducts: [],
      isGenerating: false,
      error: null,
      recommendedProducts: [],
      amazonSearchQueries: [],
      compositeImageUrl: undefined,
      productsCache: {},
    }),
}))

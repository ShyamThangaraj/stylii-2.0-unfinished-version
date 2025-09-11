"use client"

import { useState } from "react"
import { TopBar } from "@/components/top-bar"
import { Button } from "@/components/ui/button"
import { useRouter } from "next/navigation"
import { ArrowLeft } from "lucide-react"
import { useStyliiStore } from "@/lib/store"

const DESIGN_STYLES = [
  {
    id: "modern",
    name: "Modern",
    description: "Clean lines, minimal clutter, neutral colors",
    image: "/modern-living-room.png",
  },
  {
    id: "scandinavian",
    name: "Scandinavian",
    description: "Light woods, cozy textures, hygge vibes",
    image: "/scandinavian-living-room-design.jpg",
  },
  {
    id: "industrial",
    name: "Industrial",
    description: "Raw materials, exposed elements, urban feel",
    image: "/industrial-living-room-design.jpg",
  },
  {
    id: "bohemian",
    name: "Bohemian",
    description: "Eclectic patterns, rich colors, artistic flair",
    image: "/bohemian-living-room-design.jpg",
  },
  {
    id: "mid-century",
    name: "Mid-Century Modern",
    description: "Retro furniture, bold colors",
    image: "/mid-century-modern-living-room-design.jpg",
  },
  {
    id: "traditional",
    name: "Traditional",
    description: "Classic elegance, rich fabrics, timeless appeal",
    image: "/traditional-living-room-design.jpg",
  },
]

export default function ResultsPage() {
  const router = useRouter()
  const [isGenerating, setIsGenerating] = useState(false)
  const [loadingStep, setLoadingStep] = useState("")
  
  // Get form data from Zustand store
  const { images, budget, notes, selectedProducts, getProductsFromCache, setProductsCache, isGenerating: globalGenerating, setIsGenerating: setGlobalGenerating } = useStyliiStore()
  const setCompositeImageUrl = useStyliiStore((s) => s.setCompositeImageUrl)

  // Helper function to convert File to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = error => reject(error)
    })
  }

  const handleStyleSelect = async (styleId: string) => {
    // Prevent multiple clicks while already generating
    if (isGenerating || globalGenerating) {
      console.log("⏳ Already generating, please wait...")
      return
    }

    // Check if we already have products for this style
    const cached = getProductsFromCache(styleId)
    if (cached) {
      console.log("✅ Using cached products for style:", styleId)
      // Store the cached results and navigate
      useStyliiStore.getState().setRecommendedProducts(cached.products)
      useStyliiStore.getState().setAmazonSearchQueries(cached.queries)
      router.push(`/selected-design?style=${styleId}`)
      return
    }

    setIsGenerating(true)
    setGlobalGenerating(true) // Global state
    setLoadingStep("Generating your personalized design...")

    try {
      // Convert images to base64
      const imageBase64s = await Promise.all(
        images.map(file => fileToBase64(file))
      )

      // Prepare the form data with the selected style
      const formData = {
        budget: budget,
        style: styleId, // Use the selected style
        notes: notes,
        selectedProducts: selectedProducts,
        images: imageBase64s
      }

      console.log("🚀 Sending form data to backend:", formData)

      setLoadingStep("Creating search queries with AI...")

      // Call the backend API
      const response = await fetch('http://localhost:8000/api/gemini/generate-design-queries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      console.log("✅ Backend response:", result)

      setLoadingStep("Processing product recommendations...")
      
      // Simulate additional processing time
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // NEW: Generate room visualization via Nano Banana after we have products
      try {
        setLoadingStep("Compositing products into your room (AI)...")

        // Use first uploaded image as the room base (already base64 as data URL)
        const roomBase64DataUrl = imageBase64s[0]
        const roomBase64 = roomBase64DataUrl?.startsWith("data:image")
          ? roomBase64DataUrl.split(",")[1]
          : roomBase64DataUrl

        // Collect product image URLs (thumbnails) to let backend fetch server-side
        const productThumbUrls: string[] = (result.recommended_products || [])
          .map((p: any) => p?.thumbnail)
          .filter((u: any) => typeof u === "string" && u.length > 0)

        console.log("🔍 Debug - Room image:", roomBase64 ? "✅ Present" : "❌ Missing")
        console.log("🔍 Debug - Product thumbnails:", productThumbUrls.length > 0 ? `✅ ${productThumbUrls.length} found` : "❌ None found")
        console.log("🔍 Debug - Product thumbnails URLs:", productThumbUrls)

        if (roomBase64 && productThumbUrls.length > 0) {
          const nanoRes = await fetch('http://localhost:8000/api/nano-banana/generate-room-visualization', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              room_image: roomBase64,
              product_image_urls: productThumbUrls,
              prompt: 'Place each product realistically in the room, matching perspective, scale, and lighting.'
            })
          })

          if (nanoRes.ok) {
            const nanoData = await nanoRes.json()
            if (nanoData?.generated_image) {
              // Turn base64 into object URL for quick preview/logging
              const bytes = atob(nanoData.generated_image)
              const buf = new Uint8Array(bytes.length)
              for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i)
              const blob = new Blob([buf])
              const compositeUrl = URL.createObjectURL(blob)
              console.log("🖼️ Composite ready:", compositeUrl)
              setCompositeImageUrl(compositeUrl)
            }
          } else {
            const errTxt = await nanoRes.text().catch(() => "")
            console.warn("⚠️ Nano Banana call failed:", nanoRes.status, errTxt)
          }
        } else {
          console.warn("⚠️ Skipping Nano Banana: missing room image or product thumbnails.")
        }
      } catch (e) {
        console.warn("⚠️ Nano Banana step skipped due to error:", e)
      }

      setLoadingStep("Finalizing your design...")
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Store the results in Zustand store for the selected-design page
      const products = result.recommended_products || []
      const queries = result.amazon_search_queries || []
      
      useStyliiStore.getState().setRecommendedProducts(products)
      useStyliiStore.getState().setAmazonSearchQueries(queries)
      
      // Cache the results for this style
      setProductsCache(styleId, products, queries)
      console.log("💾 Cached products for style:", styleId)

      // Navigate to selected-design page with the style and results
      router.push(`/selected-design?style=${styleId}`)
      
    } catch (error) {
      console.error("❌ Error calling backend:", error)
      setLoadingStep("Error occurred. Please try again.")
      // Still redirect to selected-design for now
      setTimeout(() => {
        router.push(`/selected-design?style=${styleId}`)
      }, 2000)
    } finally {
      setIsGenerating(false)
      setGlobalGenerating(false) // Global state
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50">
      <TopBar />

      <div className="container mx-auto px-4 py-4 md:py-8">
        {/* Header */}
        <div className="mb-6 md:mb-8">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mb-4 text-orange-600 hover:text-orange-700 hover:bg-orange-100 rounded-2xl"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Form
          </Button>

          <h1 className="text-2xl md:text-4xl font-bold text-gray-900 mb-4 text-balance">Your Design Options</h1>
        </div>

        <div className="space-y-4 md:space-y-6">
          {DESIGN_STYLES.map((style, index) => (
            <div
              key={style.id}
              className="bg-white rounded-3xl overflow-hidden shadow-xl border-2 border-orange-200 hover:shadow-2xl transition-all duration-300"
            >
              <div className="aspect-[16/9] md:aspect-[16/10] bg-gray-100 relative">
                <img
                  src={style.image || "/placeholder.svg"}
                  alt={`${style.name} design style`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-3 left-3 md:top-6 md:left-6 bg-orange-500 text-white px-3 py-1 md:px-4 md:py-2 rounded-full text-xs md:text-sm font-medium">
                  ✨ Style {index + 1}
                </div>
              </div>
              <div className="p-4 md:p-8">
                <h3 className="text-xl md:text-3xl font-bold text-gray-900 mb-2 md:mb-3">{style.name}</h3>
                <p className="text-base md:text-lg text-gray-600 mb-4 md:mb-6">{style.description}</p>
                <Button
                  onClick={() => handleStyleSelect(style.id)}
                  disabled={isGenerating}
                  className="w-full md:w-auto bg-gradient-to-r from-orange-400 to-amber-400 hover:from-orange-500 hover:to-amber-500 text-white rounded-2xl py-3 md:py-4 px-6 md:px-8 text-base md:text-lg font-medium transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {isGenerating ? "Generating..." : "Choose This Design"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loading State for New Generations */}
      {isGenerating && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-3xl p-8 max-w-md mx-4 text-center">
            <div className="animate-spin w-12 h-12 border-4 border-orange-200 border-t-orange-400 rounded-full mx-auto mb-4"></div>
            <h3 className="text-lg font-semibold mb-2">Generating Your Design</h3>
            <p className="text-gray-600">{loadingStep}</p>
          </div>
        </div>
      )}
    </div>
  )
}

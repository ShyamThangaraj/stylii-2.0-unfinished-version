"use client"

import { useState, useEffect } from "react"
import { TopBar } from "@/components/top-bar"
import { Button } from "@/components/ui/button"
import { useRouter, useSearchParams } from "next/navigation"
import { ArrowLeft, Video, ExternalLink } from "lucide-react"
import { useStyliiStore } from "@/lib/store"

export default function SelectedDesignPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const styleId = searchParams.get("style") || "modern"
  
  // Get product recommendations from Zustand store
  const { recommendedProducts, budget, compositeImageUrl, setCompositeImageUrl, images } = useStyliiStore()

  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false)
  const [isGeneratingImage, setIsGeneratingImage] = useState(false)
  const [mounted, setMounted] = useState(false)
  const [rateLimitError, setRateLimitError] = useState(false)
  const [hasAttemptedGeneration, setHasAttemptedGeneration] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  // Reset generation state when style changes
  useEffect(() => {
    setHasAttemptedGeneration(false)
    setRateLimitError(false)
    setCompositeImageUrl(undefined) // Clear previous image when style changes
  }, [styleId, setCompositeImageUrl])

  // Generate composite image if not available
  useEffect(() => {
    const generateCompositeImage = async () => {
      if (!compositeImageUrl && images.length > 0 && recommendedProducts.length > 0 && !isGeneratingImage && !hasAttemptedGeneration && !rateLimitError) {
        console.log("🎨 Starting image generation...")
        setIsGeneratingImage(true)
        setHasAttemptedGeneration(true)
        
        try {
          // Convert room image to base64
          const roomFile = images[0]
          const roomBase64 = await new Promise<string>((resolve) => {
            const reader = new FileReader()
            reader.onload = () => {
              const result = reader.result as string
              // Remove data:image/...;base64, prefix
              resolve(result.split(',')[1])
            }
            reader.readAsDataURL(roomFile)
          })

          // Collect product image URLs
          const productThumbUrls: string[] = recommendedProducts
            .map((p: any) => p?.thumbnail)
            .filter((u: any) => typeof u === "string" && u.length > 0)

          if (productThumbUrls.length > 0) {
            const nanoRes = await fetch('http://localhost:8000/api/nano-banana/generate-room-visualization', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                room_image: roomBase64,
                product_image_urls: productThumbUrls,
                prompt: `Create a ${styleId} style room design. Place each product realistically in the room, matching perspective, scale, and lighting.`
              })
            })

            if (nanoRes.ok) {
              const nanoData = await nanoRes.json()
              if (nanoData?.generated_image) {
                // Convert base64 to object URL
                const bytes = atob(nanoData.generated_image)
                const buf = new Uint8Array(bytes.length)
                for (let i = 0; i < bytes.length; i++) buf[i] = bytes.charCodeAt(i)
                const blob = new Blob([buf])
                const compositeUrl = URL.createObjectURL(blob)
                setCompositeImageUrl(compositeUrl)
              }
            } else {
              const errorText = await nanoRes.text()
              console.error("❌ Nano Banana call failed:", nanoRes.status, errorText)
              
              // Handle 429 (rate limit) errors specifically
              if (nanoRes.status === 500 && errorText.includes("429")) {
                console.warn("⚠️ Gemini API rate limit reached. Please try again later.")
                setRateLimitError(true)
                // Don't retry immediately for rate limit errors
                setHasAttemptedGeneration(true)
              }
            }
          }
        } catch (error) {
          console.error("❌ Error generating composite image:", error)
        } finally {
          setIsGeneratingImage(false)
        }
      }
    }

    generateCompositeImage()
  }, [compositeImageUrl, images, recommendedProducts, styleId, setCompositeImageUrl, hasAttemptedGeneration, rateLimitError])

  const handleGenerateVideo = async () => {
    setIsGeneratingVideo(true)

    // TODO: Integrate with Fal AI to generate video
    // Placeholder for video generation logic
    setTimeout(() => {
      setIsGeneratingVideo(false)
      // TODO: Show generated video or redirect to video page
      alert("Video generation would happen here using Fal AI")
    }, 3000)
  }

  if (!mounted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50">
        <TopBar />
        <div className="container mx-auto px-4 py-8">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded mb-6 w-48"></div>
            <div className="h-96 bg-gray-200 rounded-3xl mb-6"></div>
            <div className="flex gap-4">
              <div className="h-12 bg-gray-200 rounded-2xl w-48"></div>
              <div className="h-12 bg-gray-200 rounded-2xl w-48"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // TODO: Get actual style data based on styleId
  const styleName = styleId.charAt(0).toUpperCase() + styleId.slice(1).replace("-", " ")

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-amber-50">
      <TopBar />

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <Button
            variant="ghost"
            onClick={() => router.back()}
            className="mb-4 text-orange-600 hover:text-orange-700 hover:bg-orange-100"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Results
          </Button>

          <h1 className="text-4xl font-bold text-gray-900 mb-2 text-balance">{styleName} Design</h1>
          <p className="text-xl text-gray-600">Your personalized room design with AI-generated visualization</p>
        </div>

        {/* Main Design Image */}
        <div className="bg-white rounded-3xl overflow-hidden shadow-lg border border-orange-100 mb-8">
          <div className="aspect-[16/10] bg-gray-100 relative">
            {isGeneratingImage ? (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-orange-50 to-amber-50">
                <div className="text-center">
                  <div className="animate-spin w-16 h-16 border-4 border-orange-200 border-t-orange-500 rounded-full mx-auto mb-4"></div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-2">Generating Your Design</h3>
                  <p className="text-gray-600">Creating a personalized room visualization with AI...</p>
                </div>
              </div>
            ) : rateLimitError ? (
              <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-red-50 to-orange-50">
                <div className="text-center max-w-md mx-auto px-6">
                  <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <span className="text-2xl">⚠️</span>
                  </div>
                  <h3 className="text-xl font-semibold text-gray-800 mb-2">API Rate Limit Reached</h3>
                  <p className="text-gray-600 mb-4">
                    We've hit the daily limit for AI image generation. Please try again tomorrow or contact support.
                  </p>
                  <Button 
                    onClick={() => {
                      setRateLimitError(false)
                      setHasAttemptedGeneration(false)
                    }}
                    className="bg-orange-500 hover:bg-orange-600 text-white"
                  >
                    Try Again
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <img
                  src={compositeImageUrl || `/abstract-geometric-shapes.png?height=600&width=960&query=${styleId} living room design detailed view`}
                  alt={`${styleName} room design`}
                  className="w-full h-full object-cover"
                />
                <div className="absolute top-6 left-6 bg-white/90 backdrop-blur-sm px-4 py-2 rounded-full">
                  <span className="text-sm font-medium text-gray-700">
                    {compositeImageUrl ? "AI Generated Design" : "Placeholder Design"}
                  </span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row justify-end gap-4 mb-8">
          <Button
            onClick={handleGenerateVideo}
            disabled={isGeneratingVideo}
            className="flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white rounded-2xl font-medium text-lg sm:w-auto w-full"
          >
            <Video className="w-5 h-5" />
            {isGeneratingVideo ? "Generating Video..." : "Generate Video"}
          </Button>
        </div>

        {/* Products List */}
        <div className="bg-white rounded-3xl p-8 shadow-lg border border-orange-100">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Recommended Products</h2>
              <div className="text-sm text-gray-600">
                Budget: <span className="font-semibold text-orange-600">${budget.toLocaleString()}</span>
              </div>
            </div>
            
            {recommendedProducts && recommendedProducts.length > 0 ? (
              <div className="space-y-4">
                {recommendedProducts.map((product, index) => (
                  <div
                    key={index}
                    className="flex items-start justify-between p-6 bg-orange-50 rounded-2xl hover:bg-orange-100 transition-colors"
                  >
                    <div className="flex items-start gap-4 flex-1">
                      {product.thumbnail && (
                        <img
                          src={product.thumbnail}
                          alt={product.title}
                          className="w-20 h-20 object-cover rounded-lg flex-shrink-0"
                        />
                      )}
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 text-lg mb-2 line-clamp-2">{product.title}</h3>
                        <div className="space-y-1">
                          <p className="text-orange-600 font-bold text-lg">
                            {product.price || 'Price not available'}
                          </p>
                          {product.rating && (
                            <p className="text-sm text-gray-600">
                              ⭐ {product.rating} stars
                              {product.reviews && ` (${product.reviews.toLocaleString()} reviews)`}
                            </p>
                          )}
                          {product.bought_last_month && (
                            <p className="text-xs text-green-600 font-medium">
                              🔥 {product.bought_last_month.toLocaleString()} bought in past month
                            </p>
                          )}
                          {product.delivery && product.delivery.length > 0 && (
                            <p className="text-xs text-blue-600">
                              🚚 {product.delivery.join(", ")}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                    <Button
                      asChild
                      variant="outline"
                      className="border-orange-200 text-orange-600 hover:bg-orange-50 bg-transparent flex-shrink-0 ml-4"
                    >
                      <a href={product.link_clean || product.link} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="w-4 h-4 mr-2" />
                        View on Amazon
                      </a>
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">No product recommendations available yet.</p>
                <p className="text-sm text-gray-400">
                  Make sure you've selected a design style to generate personalized recommendations.
                </p>
              </div>
            )}
          </div>

        {/* Video Generation Loading */}
        {isGeneratingVideo && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-3xl p-8 max-w-md mx-4 text-center">
              <div className="animate-spin w-12 h-12 border-4 border-purple-200 border-t-purple-500 rounded-full mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold mb-2">Generating Video</h3>
              <p className="text-gray-600">Creating a video walkthrough using Fal AI...</p>
              {/* TODO: Integrate with actual Fal AI video generation */}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

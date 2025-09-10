"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Slider } from "@/components/ui/slider"
import { Checkbox } from "@/components/ui/checkbox"
import { UploadDropzone } from "./upload-dropzone"
import { useStyliiStore } from "@/lib/store"
import { useRouter } from "next/navigation"
import { ChevronLeft, ChevronRight } from "lucide-react"

const PRODUCT_TYPES = [
  { id: "furniture", label: "Furniture", description: "Sofas, chairs, tables, beds" },
  { id: "appliances", label: "Appliances", description: "Kitchen & home appliances" },
  { id: "decor", label: "Decor", description: "Vases, plants, decorative items" },
  { id: "frames", label: "Frames & Art", description: "Wall art, mirrors, frames" },
  { id: "lighting", label: "Lighting", description: "Lamps, fixtures, ambient lighting" },
  { id: "textiles", label: "Textiles", description: "Rugs, curtains, pillows" },
]

export function MultiStepDesignForm() {
  const [currentStep, setCurrentStep] = useState(0)
  const [mounted, setMounted] = useState(false)

  const { images, budget, notes, selectedProducts, setBudget, setNotes, setSelectedProducts } = useStyliiStore()
  const router = useRouter()

  useEffect(() => {
    setMounted(true)
  }, [])

  const steps = [
    {
      title: "What's your budget?",
      subtitle: "Help us find products within your price range",
      component: <BudgetStep budget={budget} setBudget={setBudget} />,
    },
    {
      title: "Upload your room photo",
      subtitle: "Share 1 photo of your space for the best results",
      component: <PhotoStep />,
    },
    {
      title: "What products are you looking for?",
      subtitle: "Select the types of items you'd like to focus on",
      component: <ProductTypesStep selectedProducts={selectedProducts} setSelectedProducts={setSelectedProducts} />,
    },
    {
      title: "Any special requests?",
      subtitle: "Tell us about your preferences or specific needs",
      component: <NotesStep notes={notes} setNotes={setNotes} />,
    },
  ]

  const canProceed = () => {
    switch (currentStep) {
      case 0: // Budget step
        return budget > 0
      case 1: // Photo step
        return images.length >= 1
      case 2: // Product types step
        return selectedProducts.length > 0
      case 3: // Notes step
        return true
      default:
        return false
    }
  }

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = () => {
    // Form data is already saved in Zustand store
    console.log("✅ Form data saved:", {
      budget: budget,
      notes: notes,
      selectedProducts: selectedProducts
    })

    // Redirect to results page to show design style options
    router.push("/results")
  }

  if (!mounted) {
    return (
      <div className="bg-white rounded-3xl p-8 shadow-lg animate-pulse">
        <div className="h-8 bg-gray-200 rounded mb-6"></div>
        <div className="h-64 bg-gray-200 rounded"></div>
      </div>
    )
  }


  return (
    <div className="bg-white rounded-2xl md:rounded-3xl p-4 md:p-8 shadow-lg border border-orange-100">
      {/* Progress Bar */}
      <div className="mb-6 md:mb-8">
        <div className="flex justify-between items-center mb-4">
          <span className="text-xs md:text-sm font-medium text-orange-600">
            Step {currentStep + 1} of {steps.length}
          </span>
          <span className="text-xs md:text-sm text-gray-500">
            {Math.round(((currentStep + 1) / steps.length) * 100)}% Complete
          </span>
        </div>
        <div className="w-full bg-orange-100 rounded-full h-2">
          <div
            className="bg-gradient-to-r from-orange-400 to-amber-400 h-2 rounded-full transition-all duration-300"
            style={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Step Content */}
      <div className="mb-6 md:mb-8">
        <h1 className="text-xl md:text-3xl font-bold text-gray-900 mb-2 text-balance">{steps[currentStep].title}</h1>
        <p className="text-gray-600 text-base md:text-lg mb-6 md:mb-8">{steps[currentStep].subtitle}</p>

        <div className="min-h-[250px] md:min-h-[300px]">{steps[currentStep].component}</div>
      </div>

      {/* Navigation */}
      <div className="flex flex-col md:flex-row justify-between items-center gap-4 md:gap-0">
        <Button
          variant="outline"
          onClick={handlePrevious}
          disabled={currentStep === 0}
          className="w-full md:w-auto flex items-center justify-center gap-2 px-6 py-3 rounded-2xl border-orange-200 text-orange-600 hover:bg-orange-50 bg-transparent order-2 md:order-1"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </Button>

        {currentStep === steps.length - 1 ? (
          <Button
            onClick={handleSubmit}
            disabled={!canProceed()}
            className="w-full md:w-auto flex items-center justify-center gap-2 px-8 py-3 bg-gradient-to-r from-orange-400 to-amber-400 hover:from-orange-500 hover:to-amber-500 text-white rounded-2xl font-medium order-1 md:order-2"
          >
            Choose Design
            <ChevronRight className="w-4 h-4" />
          </Button>
        ) : (
          <Button
            onClick={handleNext}
            disabled={!canProceed()}
            className="w-full md:w-auto flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-400 to-amber-400 hover:from-orange-500 hover:to-amber-500 text-white rounded-2xl order-1 md:order-2"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </Button>
        )}
      </div>
    </div>
  )
}

function BudgetStep({ budget, setBudget }: { budget: number; setBudget: (budget: number) => void }) {
  return (
    <div className="space-y-4 md:space-y-6">
      <div className="space-y-4">
        <Input
          type="number"
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          placeholder="Enter your budget"
          className="text-xl md:text-2xl p-4 md:p-6 rounded-2xl border-orange-200 focus:border-orange-400 text-center"
        />
        <div className="px-2 md:px-4">
          <Slider
            value={[budget]}
            onValueChange={([value]) => setBudget(value)}
            max={20000}
            min={500}
            step={100}
            className="w-full"
          />
          <div className="flex justify-between text-xs md:text-sm text-gray-500 mt-2">
            <span>$500</span>
            <span className="font-bold text-orange-600 text-base md:text-lg">${budget.toLocaleString()}</span>
            <span>$20,000+</span>
          </div>
        </div>
      </div>
      <div className="bg-orange-50 rounded-2xl p-4 md:p-6">
        <p className="text-orange-800 text-xs md:text-sm">
          💡 <strong>Tip:</strong> Your budget helps us recommend products that fit your price range and prioritize the
          most impactful changes.
        </p>
      </div>
    </div>
  )
}

function PhotoStep() {
  return (
    <div className="space-y-6">
      <UploadDropzone />
      <div className="bg-amber-50 rounded-2xl p-6">
        <p className="text-amber-800 text-sm">
          📸 <strong>Best results:</strong> Include photos from different angles, good lighting, and show the entire
          room when possible.
        </p>
      </div>
    </div>
  )
}

function ProductTypesStep({
  selectedProducts,
  setSelectedProducts,
}: {
  selectedProducts: string[]
  setSelectedProducts: (products: string[]) => void
}) {
  const toggleProduct = (productId: string) => {
    setSelectedProducts(
      selectedProducts.includes(productId)
        ? selectedProducts.filter((id) => id !== productId)
        : [...selectedProducts, productId],
    )
  }

  return (
    <div className="space-y-4 md:space-y-6">
      <div className="grid grid-cols-1 gap-3 md:gap-4">
        {PRODUCT_TYPES.map((product) => (
          <div
            key={product.id}
            className={`p-3 md:p-4 rounded-2xl border-2 cursor-pointer transition-all ${
              selectedProducts.includes(product.id)
                ? "border-orange-400 bg-orange-50"
                : "border-gray-200 hover:border-orange-200 hover:bg-orange-25"
            }`}
            onClick={() => toggleProduct(product.id)}
          >
            <div className="flex items-start gap-3">
              <Checkbox
                checked={selectedProducts.includes(product.id)}
                onChange={() => toggleProduct(product.id)}
                className="mt-1"
              />
              <div>
                <h3 className="font-semibold text-gray-900 text-sm md:text-base">{product.label}</h3>
                <p className="text-xs md:text-sm text-gray-600">{product.description}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="bg-orange-50 rounded-2xl p-4 md:p-6">
        <p className="text-orange-800 text-xs md:text-sm">
          🎯 <strong>Focus areas:</strong> Select the product types you're most interested in updating. Our AI will
          prioritize these in your design.
        </p>
      </div>
    </div>
  )
}


function NotesStep({ notes, setNotes }: { notes: string; setNotes: (notes: string) => void }) {
  return (
    <div className="space-y-4 md:space-y-6">
      <Textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Tell us about your style preferences, color likes/dislikes, or any specific requirements..."
        className="min-h-[150px] md:min-h-[200px] p-4 md:p-6 rounded-2xl border-orange-200 focus:border-orange-400 text-base md:text-lg"
      />
      <div className="bg-orange-50 rounded-2xl p-4 md:p-6">
        <p className="text-orange-800 text-xs md:text-sm">
          ✨ <strong>Optional but helpful:</strong> The more details you share, the better we can personalize your
          design recommendations.
        </p>
      </div>
    </div>
  )
}

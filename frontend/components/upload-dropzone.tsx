"use client"

import { useCallback, useState } from "react"
import { useDropzone } from "react-dropzone"
import { X, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useStyliiStore } from "@/lib/store"

export function UploadDropzone() {
  const { images, setImages } = useStyliiStore()
  const [isDragActive, setIsDragActive] = useState(false)

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      // Only keep the first file (limit to 1 image)
      const newImages = acceptedFiles.slice(0, 1)
      setImages(newImages)
    },
    [setImages],
  )

  const { getRootProps, getInputProps } = useDropzone({
    onDrop,
    accept: {
      "image/*": [".jpeg", ".jpg", ".png", ".webp"],
    },
    maxFiles: 1,
    disabled: images.length >= 1,
    onDragEnter: () => setIsDragActive(true),
    onDragLeave: () => setIsDragActive(false),
  })

  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index)
    setImages(newImages)
  }

  return (
    <div className="space-y-4">
      {images.length < 1 && (
        <div className="space-y-3">
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-6 md:p-8 text-center cursor-pointer transition-colors ${
              isDragActive ? "border-orange-400 bg-orange-50" : "border-gray-300 hover:border-orange-400"
            }`}
          >
            <input {...getInputProps()} />
            <Upload className="w-8 h-8 md:w-12 md:h-12 mx-auto mb-3 md:mb-4 text-gray-400" />
            <p className="text-base md:text-lg font-medium mb-2">
              {isDragActive ? "Drop image here" : "Drag & drop room photo"}
            </p>
            <p className="text-sm md:text-base text-gray-500">or click to browse</p>
          </div>
        </div>
      )}

      {images.length > 0 && (
        <div className="space-y-3">
          {images.map((image, index) => (
            <div key={index} className="relative group">
              <img
                src={URL.createObjectURL(image) || "/placeholder.svg"}
                alt={`Room photo ${index + 1}`}
                className="w-full h-48 md:h-64 object-cover rounded-lg"
              />
              <Button
                size="sm"
                variant="destructive"
                className="absolute top-2 right-2 w-6 h-6 md:w-8 md:h-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => removeImage(index)}
              >
                <X className="w-4 h-4 md:w-5 md:h-5" />
              </Button>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs md:text-sm text-gray-500">
        {images.length}/1 photo uploaded
        {images.length >= 1 && <span className="text-green-600 ml-2">✓ Ready to generate</span>}
      </p>
    </div>
  )
}

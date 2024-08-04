import React, { useState, useEffect } from "react";

const ImageGallery = () => {
  const [images, setImages] = useState([]);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [currentImage, setCurrentImage] = useState(null);

  useEffect(() => {
    const importImages = async () => {
      const imageModules = import.meta.glob("/public/screenshots/*.{png,jpg,jpeg}");
      const imagePromises = Object.keys(imageModules).map((path) => {
        const src = path.replace("/public", "");
        return { src, alt: path };
      });

      setImages(imagePromises);
    };

    importImages();
  }, []);

  const openFullscreen = (image) => {
    setCurrentImage(image);
    setIsFullscreen(true);
  };

  const closeFullscreen = () => {
    setIsFullscreen(false);
    setCurrentImage(null);
  };

  return (
    <div className=''>
      <div className='grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4'>
        {images.map((image, index) => (
          <div key={index} className='overflow-hidden rounded-md border hover:border-gray-500'>
            <img
              src={image.src}
              alt={`Screenshot ${index + 1}`}
              className='w-full h-auto cursor-pointer'
              onClick={() => openFullscreen(image.src)}
            />
          </div>
        ))}
      </div>

      {isFullscreen && (
        <div
          className='fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50 p-10'
          onClick={closeFullscreen}
        >
          <img
            src={currentImage}
            alt='Fullscreen'
            className='max-w-full max-h-full rounded-md'
            onClick={(e) => e.stopPropagation()}
          />
          <button className='absolute top-6 right-10 text-white text-3xl' onClick={closeFullscreen}>
            &times;
          </button>
        </div>
      )}
    </div>
  );
};

export default ImageGallery;

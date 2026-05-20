import { z } from 'zod';

// Categorias fixas do sistema
export const PRODUCT_CATEGORIES = ['Casual', 'Social', 'Esportivo', 'Feminino', 'Masculino', 'Infantil'];

// Schema para criação/edição de produto
export const ProductSchema = z.object({
  titulo: z
    .string()
    .min(1, 'Título é obrigatório')
    .min(3, 'Título deve ter pelo menos 3 caracteres')
    .max(100, 'Título não pode ter mais de 100 caracteres')
    .trim(),
  preco: z
    .union([z.string(), z.number()])
    .refine((val) => {
      const num = typeof val === 'string' ? parseFloat(val) : val;
      return !isNaN(num) && num > 0;
    }, {
      message: 'Preço deve ser um número válido maior que 0'
    })
    .transform((val) => typeof val === 'string' ? parseFloat(val) : val),
  descricao: z
    .string()
    .min(1, 'Descrição é obrigatória')
    .min(10, 'Descrição deve ter pelo menos 10 caracteres')
    .max(500, 'Descrição não pode ter mais de 500 caracteres')
    .trim(),
  categoria: z
    .string()
    .min(1, 'Categoria é obrigatória')
    .refine((val) => PRODUCT_CATEGORIES.includes(val), {
      message: `Categoria deve ser uma das opções: ${PRODUCT_CATEGORIES.join(', ')}`
    }),
  imagem: z
    .string()
    .optional()
    .nullable()
    .transform((val) => val || '')
});

// Schema para validação de imagem
export const ImageSchema = z.object({
  file: z
    .instanceof(File)
    .refine((file) => file.size <= 5 * 1024 * 1024, {
      message: 'Imagem deve ter no máximo 5MB'
    })
    .refine(
      (file) => ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'].includes(file.type),
      {
        message: 'Formato de imagem inválido. Use: JPG, PNG, GIF ou WEBP'
      }
    )
});

// Hook personalizado para validação de produtos
export const useProductValidation = () => {
  const validate = (data) => {
    try {
      const result = ProductSchema.parse(data);
      return { success: true, data: result, errors: null };
    } catch (error) {
      if (error instanceof z.ZodError && error.errors && Array.isArray(error.errors)) {
        const errors = {};
        error.errors.forEach((err) => {
          const path = err.path && err.path.length > 0 ? err.path.join('.') : 'general';
          errors[path] = err.message;
        });
        return { success: false, data: null, errors };
      }
      console.error('Erro de validação:', error);
      return { success: false, data: null, errors: { general: error?.message || 'Erro de validação' } };
    }
  };

  const validateImage = (file) => {
    try {
      ImageSchema.parse({ file });
      return { success: true, error: null };
    } catch (error) {
      if (error instanceof z.ZodError) {
        return { success: false, error: error.errors[0]?.message || 'Imagem inválida' };
      }
      return { success: false, error: 'Erro ao validar imagem' };
    }
  };

  return { validate, validateImage };
};

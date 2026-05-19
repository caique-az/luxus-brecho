import { Stack } from "expo-router";
import { ToastProvider } from "../contexts/ToastContext";

export default function Layout() {
  return (
    <ToastProvider>
      <Stack
        screenOptions={{
          headerShown: false, // Ocultar header em todas as telas
        }}>
        <Stack.Screen 
          name="(tabs)" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="product/[id]" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="login" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="register" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="profile" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="search" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="categories" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="category/[id]" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="support" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="contact" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="account-settings" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="settings/address" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="settings/password" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="settings/email" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="admin/create-product" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="admin/manage-products" 
          options={{ headerShown: false }} 
        />
        <Stack.Screen 
          name="admin/edit-product/[id]" 
          options={{ headerShown: false }} 
        />
      </Stack>
    </ToastProvider>
  );
}

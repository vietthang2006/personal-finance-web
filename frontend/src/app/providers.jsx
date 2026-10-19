import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/features/auth";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,                     // lỗi thì thử lại 1 lần
      refetchOnWindowFocus: false,  // không tự tải lại khi quay lại tab
    },
  },
});

export default function Providers({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
        <AuthProvider>
            {children}
        </AuthProvider>
    </QueryClientProvider>
  );
}
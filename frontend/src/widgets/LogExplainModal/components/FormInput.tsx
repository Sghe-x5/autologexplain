import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export const FormInput = ({
  className,
  ...props
}: React.ComponentProps<"input">) => {
  return (
    <Input
      {...props}
      className={cn(
        className,
        "hover:border-1 hover:border-[#2463EB] ease-in transition-all"
      )}
    />
  );
};
